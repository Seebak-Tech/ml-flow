import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_ecs as ecs,
    aws_rds as rds,
    aws_iam as iam,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_secretsmanager as sm,
    aws_ecs_patterns as ecs_patterns,
    CfnParameter,
    Stack
)


class MlFlowStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # ==============================
        # ======= CFN PARAMETERS =======
        # ==============================
        project_name_param = CfnParameter(
            scope=self,
            id='ProjectName',
            type='String',
            default='mlflow'
        )

        db_name = 'mlflowdb'
        port = 3306
        username = 'master'
        bucket_name = (
            f'{project_name_param.value_as_string}-artifacts-'
            f'{cdk.Aws.ACCOUNT_ID}'
        )

        container_repo_name = 'mlflow-containers'
        cluster_name = 'mlflow_clus'
        service_name = 'mlflow_serv'

        # ==================================================
        # ================= IAM ROLE =======================
        # ==================================================
        role = iam.Role(
            scope=self,
            id='TASKROLE',
            assumed_by=iam.ServicePrincipal(service='ecs-tasks.amazonaws.com')
        )

        role.add_managed_policy(
            iam.ManagedPolicy
               .from_aws_managed_policy_name('AmazonS3FullAccess')
        )

        role.add_managed_policy(
            iam.ManagedPolicy
               .from_aws_managed_policy_name('AmazonECS_FullAccess')
        )

        # ==================================================
        # ================== SECRET ========================
        # ==================================================
        db_password_secret = sm.Secret(
            scope=self,
            id='DBSECRET',
            secret_name='dbPassword',
            generate_secret_string=sm.SecretStringGenerator(
                password_length=20,
                exclude_punctuation=True
            )
        )

        # ==================================================
        # ==================== VPC =========================
        # ==================================================
        public_subnet = ec2.SubnetConfiguration(
            name='Public',
            subnet_type=ec2.SubnetType.PUBLIC,
            cidr_mask=28
        )

        private_subnet = ec2.SubnetConfiguration(
            name='Private',
            subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT,
            cidr_mask=28
        )

        isolated_subnet = ec2.SubnetConfiguration(
            name='DB',
            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            cidr_mask=28
        )

        nat_gateway_instance = ec2.NatProvider.instance(
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=ec2.GenericLinuxImage(
                ami_map={
                    'us-west-2': 'ami-0a4bc8a5c1ed3b5a3'
                }
            )
        )

        vpc = ec2.Vpc(
            scope=self,
            id='VPC',
            cidr='10.0.0.0/24',
            max_azs=2,
            nat_gateway_provider=nat_gateway_instance,
            nat_gateways=1,
            subnet_configuration=[public_subnet,
                                  private_subnet,
                                  isolated_subnet]
        )

        vpc.add_gateway_endpoint(
            'S3Endpoint',
            service=ec2.GatewayVpcEndpointAwsService.S3
        )

        # ==================================================
        # ================= S3 BUCKET ======================
        # ==================================================
        artifact_bucket = s3.Bucket(
            scope=self,
            id='ARTIFACTBUCKET',
            bucket_name=bucket_name,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        # # ==================================================
        # # ================== DATABASE  =====================
        # # ==================================================
        # Creates a security group for AWS RDS
        sg_rds = ec2.SecurityGroup(
            scope=self,
            id='SGRDS',
            vpc=vpc,
            security_group_name='sg_rds'
        )
        # Adds an ingress rule which allows resources in the VPC's
        # CIDR to access the database.
        sg_rds.add_ingress_rule(
            peer=ec2.Peer.ipv4('10.0.0.0/24'),
            connection=ec2.Port.tcp(port)
        )

        database = rds.DatabaseInstance(
            scope=self,
            id='MYSQL',
            database_name=db_name,
            port=port,
            credentials=rds.Credentials.from_password(
                username=username,
                password=db_password_secret.secret_value
            ),
            allocated_storage=20,
            engine=rds.DatabaseInstanceEngine.mysql(
                version=rds.MysqlEngineVersion.VER_8_0_23
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE2,
                ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            security_groups=[sg_rds],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            # multi_az=True,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            deletion_protection=False
        )

        # ==================================================
        # =============== ECS SERVICE ==================
        # ==================================================
        cluster = ecs.Cluster(
            scope=self,
            id='CLUSTER',
            capacity=ecs.AddCapacityOptions(
                instance_type=ec2.InstanceType("t2.micro"),
                desired_capacity=1,
                max_capacity=1
            ),
            cluster_name=cluster_name,
            vpc=vpc
        )

        task_definition = ecs.Ec2TaskDefinition(
            scope=self,
            id='MLflow',
            task_role=role,
        )

        container = task_definition.add_container(
            id='Container',
            image=ecs.ContainerImage.from_asset(
                directory='container'
            ),
            memory_limit_mib=800,
            environment={
                'BUCKET': f's3://{artifact_bucket.bucket_name}',
                'HOST': database.db_instance_endpoint_address,
                'PORT': str(port),
                'DATABASE': db_name,
                'USERNAME': username
            },
            secrets={
                'PASSWORD': ecs.Secret.from_secrets_manager(db_password_secret)
            }
        )

        port_mapping = ecs.PortMapping(
            container_port=5000,
            host_port=5000,
            protocol=ecs.Protocol.TCP
        )

        container.add_port_mappings(port_mapping)

        ml_flow_service = ecs_patterns.ApplicationLoadBalancedEc2Service(
            scope=self,
            id='MLFLOW',
            service_name=service_name,
            cluster=cluster,
            task_definition=task_definition
        )

        route53_hosted_zone = route53.HostedZone.from_lookup(
            scope=self,
            id="HostedZone",
            domain_name="seebak.com.mx"
        )
        record = route53.ARecord(
            scope=self,
            id="AliasRecord",
            zone=route53_hosted_zone,
            target=route53.RecordTarget.from_alias(
                targets.LoadBalancerTarget(
                    ml_flow_service.load_balancer
                )
            ),
            record_name="mlflow.srvc"
        )

        # Setup security group
        ml_flow_service.service \
                       .connections \
                       .security_groups[0] \
                       .add_ingress_rule(
                           peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
                           connection=ec2.Port.tcp(5000),
                           description='Allow inbound from VPC for mlflow'
                        )

        # ==================================================
        # =================== OUTPUTS ======================
        # ==================================================
        cdk.CfnOutput(
            scope=self,
            id='URL',
            value=record.domain_name
        )
