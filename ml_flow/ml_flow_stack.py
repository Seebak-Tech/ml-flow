import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_s3 as s3,
    #  aws_ecs as ecs,
    aws_rds as rds,
    aws_iam as iam,
    aws_secretsmanager as sm,
    #  aws_ecs_patterns as ecs_patterns,
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
        #  container_repo_name = 'mlflow-containers'
        #  cluster_name = 'mlflow'
        #  service_name = 'mlflow'

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
            subnet_type=ec2.SubnetType.PRIVATE,
            cidr_mask=28
        )

        isolated_subnet = ec2.SubnetConfiguration(
            name='DB',
            subnet_type=ec2.SubnetType.ISOLATED,
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
                subnet_type=ec2.SubnetType.ISOLATED
            ),
            # multi_az=True,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            deletion_protection=False
        )
