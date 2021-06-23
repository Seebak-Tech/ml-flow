from aws_cdk import Stack
from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_ecs as ecs,
    aws_rds as rds,
    aws_iam as iam,
    aws_secretsmanager as sm,
    aws_ecs_patterns as ecs_patterns,
    CfnParameter
)


class MlFlowStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # ==============================
        # ======= CFN PARAMETERS =======
        # ==============================
        #  project_name_param = CfnParameter(
        #  scope=self,
        #  id='ML-FLow',
        #  type='String'
        #  )

        #  db_name = 'mlflowdb'
        #  port = 3306
        #  username = 'master'
        #  bucket_name = (
        #  f'{project_name_param.value_as_string}-artifacts- \
        #  {core.Aws.ACCOUNT_ID}'
        #  )
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

        vpc = ec2.Vpc(
            scope=self,
            id='VPC',
            cidr='10.0.0.0/24',
            max_azs=2,
            nat_gateway_provider=ec2.NatProvider.gateway(),
            nat_gateways=1,
            subnet_configuration=[public_subnet,
                                  private_subnet,
                                  isolated_subnet]
        )

        vpc.add_gateway_endpoint(
            'S3Endpoint',
            service=ec2.GatewayVpcEndpointAwsService.S3
        )
