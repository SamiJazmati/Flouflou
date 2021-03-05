import argparse
import os
import subprocess

from aws_manager import (
    CodeBuildClient,
    CodeStarClient,
    ElasticBeanstalkClient,
    ELBOptionSettings,
    Route53Client,
    Route53HostedZoneId,
)
from messaging_manager import ChannelURL, Colors, SlackClient
from models import FastAPI, JSFrameworks, PythonFrameworks, React
from repo_manager import GithubClient, GitIgnoreTemplate
from utils import utils

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class ServiceCreator:
    def __init__(
        self,
        user,
        organisation,
        service,
        framework,
        repoManagerClient,
        messageClient,
        continuousIntegrationClient,
        notificationClient,
        orchestratorClient,
        dnsClient,
    ):
        self.user = user
        self.organisation = organisation
        self.service = service
        self.framework = framework
        self.repoManagerClient = repoManagerClient
        self.messageClient = messageClient
        self.continuousIntegrationClient = continuousIntegrationClient
        self.notificationClient = notificationClient
        self.orchestratorClient = orchestratorClient
        self.dnsClient = dnsClient

    def create_repo(
        self,
        autoInit=True,
        description='',
        private=True,
        deleteBranchOnMerge=True,
    ):
        self.messageClient.send_slack(
            channel=ChannelURL.DEVS,
            message=f'{self.user} has begun the creation of service {self.service}',
            colour=Colors.WARNING,
        )
        if self.framework in PythonFrameworks.ALL:
            gitignoreTemplate = GitIgnoreTemplate.PYTHON
            if self.framework == 'fast_api':
                self.template = FastAPI()
        elif self.framework in JSFrameworks.ALL:
            gitignoreTemplate = GitIgnoreTemplate.NODE
            if self.framework == 'react':
                self.template = React()
        else:
            self.messageClient.send_slack(
                channel=ChannelURL.DEVS,
                message=f'Creation of service {self.service} failed',
                colour=Colors.DANGER,
            )
            raise SystemExit(
                'Please select a valid framework (ex: react, fast_api, ...)'
            )
        self.repoManagerClient.create_repo(
            repoName=self.repoName,
            organisationName=self.organisation,
            gitignoreTemplate=gitignoreTemplate,
            autoInit=autoInit,
            description=description,
            private=private,
            deleteBranchOnMerge=deleteBranchOnMerge,
        )
        return self.messageClient.send_slack(
            channel=ChannelURL.DEVS,
            message=f'Service {self.service} has been created successfully.',
            colour=Colors.GOOD,
        )

    @staticmethod
    def generate_ssh_key():
        email = os.environ.get('EMAIL')
        try:
            return subprocess.call(['sh', './scripts/generate_ssh_key.sh', email])
        except subprocess.CalledProcessError:
            raise SystemExit('Error: Could not generate ssh key file.')

    @staticmethod
    def get_ssh_key():
        try:
            key = subprocess.check_output(['cat', 'id_rsa.pub'], cwd='../../../.ssh')
        except subprocess.CalledProcessError:
            raise SystemExit('Error: Could not get public key generated')
        return key.strip().decode("utf-8")

    def add_ssh_key_to_repo(self):
        key = self.get_ssh_key()
        self.repo = self.repoManagerClient.get_repo(
            owner=self.organisation, repoName=self.repoName
        )
        return self.repoManagerClient.create_ssh_key_for_repo(
            repo=self.repo, title=f'{self.user}-{self.service}-ssh-key', key=key
        )

    def pull_repo(self):
        self.messageClient.send_slack(
            channel=ChannelURL.DEVS,
            message=f'Starting git and CI/CD configurations for service {self.service}',
            colour=Colors.WARNING,
        )
        try:
            return subprocess.check_output(
                ['git', 'clone', f'{self.repo.ssh_url}'], cwd='..'
            )
        except subprocess.CalledProcessError:
            self.messageClient.send_slack(
                channel=ChannelURL.DEVS,
                message=f'Git and CI/CD configurations for service {self.service} failed',
                colour=Colors.DANGER,
            )
            raise SystemExit(
                f'Error: Could not pull repo {self.repoName}, are you sure that the repo exists or the ssh connexion has been setup properly?'
            )

    def clean_ssh_repo(self):
        keyFile = f'{os.environ.get("KEY")}{self.service}'
        try:
            return subprocess.call(
                ['sh', './scripts/clean_ssh_repo.sh', keyFile, self.repoName]
            )
        except subprocess.CalledProcessError:
            self.messageClient.send_slack(
                channel=ChannelURL.DEVS,
                message=f'Git and CI/CD configurations for service {self.service} failed',
                colour=Colors.DANGER,
            )
            raise SystemExit('Error: Could not run clean ssh repo bash script properly')

    def update_git_config(self):
        self.cwd = f'../{self.repoName}'
        gitCwd = f'{self.cwd}/.git'
        try:
            return subprocess.call(
                [
                    'sed',
                    '-i',
                    '_backup',
                    f's#git@github.com:{self.organisation}/{self.repoName}.git#ssh://git@{self.repoName}/{self.organisation}/{self.repoName}.git#',
                    'config',
                ],
                cwd=gitCwd,
            )
        except subprocess.CalledProcessError:
            self.messageClient.send_slack(
                channel=ChannelURL.DEVS,
                message=f'Git and CI/CD configurations for service {self.service} failed',
                colour=Colors.DANGER,
            )
            raise SystemExit('Error: Could not update git config file.')

    def set_default_branch(self):
        try:
            subprocess.check_output(['git', 'checkout', '-b', 'develop'], cwd=self.cwd)
            subprocess.check_output(
                ['git', 'push', '--set-upstream', 'origin', 'develop'], cwd=self.cwd
            )
        except subprocess.CalledProcessError:
            self.messageClient.send_slack(
                channel=ChannelURL.DEVS,
                message=f'Git and CI/CD configurations for service {self.service} failed',
                colour=Colors.DANGER,
            )
            raise SystemExit('Error: Could not create and push new develop branch')
        return self.repoManagerClient.edit_default_branch_for_repo(
            repo=self.repo, defaultBranch='develop'
        )

    def create_build(self):
        self.awsAccountId = os.environ.get('AWS_ACCOUNT_ID')
        self.awsRegion = os.environ.get("AWS_REGION")
        return self.continuousIntegrationClient.create_build(
            name=f'{self.service}-build',
            description='Build and test docker images',
            source={
                'type': 'GITHUB',
                'location': f'https://github.com/{self.organisation}/{self.repoName}.git',
                'gitCloneDepth': 1,
                'gitSubmodulesConfig': {'fetchSubmodules': False},
                'reportBuildStatus': True,
                'insecureSsl': False,
            },
            secondarySources=[],
            secondarySourceVersions=[],
            artifacts={'type': 'NO_ARTIFACTS'},
            secondaryArtifacts=[],
            cache={'type': 'NO_CACHE'},
            environment={
                'type': 'LINUX_CONTAINER',
                'image': 'aws/codebuild/standard:5.0',
                'computeType': 'BUILD_GENERAL1_SMALL',
                'environmentVariables': [
                    {
                        'name': 'AWS_ACCOUNT_ID',
                        'value': f'{self.awsAccountId}',
                        'type': 'PLAINTEXT',
                    }
                ],
                'privilegedMode': True,
                'imagePullCredentialsType': 'CODEBUILD',
            },
            serviceRole=f'arn:aws:iam::{self.awsAccountId}:role/CodeBuildServiceRole',
            timeoutInMinutes=29,
            queuedTimeoutInMinutes=480,
            encryptionKey=f'arn:aws:kms:{self.awsRegion}:{self.awsAccountId}:alias/aws/s3',
            tags=[],
            badgeEnabled=True,
            logsConfig={
                'cloudWatchLogs': {'status': 'ENABLED'},
                's3Logs': {'status': 'DISABLED', 'encryptionDisabled': False},
            },
        )

    def create_webhook(self):
        return self.continuousIntegrationClient.create_webhook(
            projectName=f'{self.service}-build',
            filterGroups=[
                [
                    {
                        'type': 'EVENT',
                        'pattern': 'PUSH',
                        'excludeMatchedPattern': False,
                    },
                ],
            ],
            buildType='BUILD',
        )

    def create_build_notification(self):
        return self.notificationClient.create_notification_rule(
            name=f'{self.repoName} Build Status',
            eventTypeIds=[
                'codebuild-project-build-state-failed',
                'codebuild-project-build-state-stopped',
                'codebuild-project-build-state-succeeded',
            ],
            resource=f'arn:aws:codebuild:{self.awsRegion}:{self.awsAccountId}:project/{self.service}-build',
            targets=[
                {
                    'TargetAddress': f'arn:aws:chatbot::{self.awsAccountId}:chat-configuration/slack-channel/BuildStatus',
                    'TargetType': 'AWSChatbotSlack',
                }
            ],
            detailType='FULL',
            status='ENABLED',
        )

    def add_template(self, template):
        if template:
            try:
                subprocess.check_output(['rm', '-f', '.gitignore'], cwd=self.cwd)
                subprocess.check_output(
                    [
                        'rsync',
                        '-av',
                        f'../{self.template.REPO}/.',
                        self.cwd,
                        '--exclude=README.md',
                        '--exclude=.git',
                        '--exclude=.DS_Store',
                    ]
                )
            except subprocess.CalledProcessError:
                self.messageClient.send_slack(
                    channel=ChannelURL.DEVS,
                    message=f'Git and CI/CD configurations for service {self.service} failed',
                    colour=Colors.DANGER,
                )
                raise SystemExit(
                    f'Error: Could not copy and paste skeleton {self.template.REPO} in {self.cwd}'
                )
            utils.templates_to_files(
                templateFiles=self.template.TEMPLATE_FILES,
                values={
                    self.template.REPO: self.repoName,
                    self.template.SERVICE: self.service,
                },
                cwd=self.cwd,
                deleteBackup=True,
            )

            [
                utils.rename_file_or_folder(
                    originalName=originalName,
                    newName=originalName.replace(self.template.SERVICE, self.service),
                    cwd=self.cwd,
                )
                for originalName in self.template.FILES_AND_REPOS
            ]
        else:
            utils.template_to_file(
                templateFile='buildspec.yaml',
                values={'awsRegion': self.awsRegion},
                cwd='templates',
                destination=self.cwd,
            )
        try:
            subprocess.check_output(['git', 'add', '.'], cwd=self.cwd)
            subprocess.check_output(
                ['git', 'commit', '-m', '"add skeleton"'], cwd=self.cwd
            )
            return subprocess.check_output(['git', 'push'], cwd=self.cwd)
        except subprocess.CalledProcessError:
            self.messageClient.send_slack(
                channel=ChannelURL.DEVS,
                message=f'Git and CI/CD configurations for service {self.service} failed',
                colour=Colors.DANGER,
            )
            raise SystemExit(
                'Error: Could not commit and push the new added and generated files from skeleton'
            )

    def trigger_build(self):
        return self.continuousIntegrationClient.trigger_last_build()

    def add_branch_protection_rules(self):
        [
            self.repoManagerClient.edit_branch_protection_rules(
                repo=self.repo,
                branchName=branchName,
                strict=True,
                contexts=[f'AWS CodeBuild eu-west-2 ({self.service}-build)'],
                enforceAdmins=True,
            )
            for branchName in ['develop', 'master']
        ]
        return self.messageClient.send_slack(
            channel=ChannelURL.DEVS,
            message=f'Git configuration for service {self.service} has been created successfully. '
            f'Branches, build and notifications have been properly configured',
            colour=Colors.GOOD,
        )

    def host_service(self):
        self.messageClient.send_slack(
            channel=ChannelURL.DEVS,
            message=f'Creation of application {self.service} with environments {self.service}-staging, {self.service}-live on Elasticbeanstalk',
            colour=Colors.WARNING,
        )
        self.environmentNames = [f'{self.service}-staging', f'{self.service}-live']
        try:
            self.orchestratorClient.create_application(
                applicationName=self.service, description='', tags=[]
            )
            [
                self.orchestratorClient.create_environment(
                    applicationName=self.service,
                    environmentName=environmentName,
                    description='',
                    tier={'Name': 'WebServer', 'Type': 'Standard', 'Version': '1.0'},
                    solutionStackName='64bit Amazon Linux 2018.03 v2.16.5 running Docker 19.03.13-ce',
                    optionSettings=[
                        {
                            'Namespace': ELBOptionSettings.NAMESPACE,
                            'OptionName': ELBOptionSettings.OPTIONNAME,
                            'Value': ELBOptionSettings.VALUE,
                        },
                    ],
                )
                for environmentName in self.environmentNames
            ]
            subprocess.check_output(['mkdir', '.elasticbeanstalk'], cwd=self.cwd)
            utils.template_to_file(
                templateFile='eb_config.yml',
                values={'serviceName': self.service},
                cwd='templates',
                destination=f'{self.cwd}/.elasticbeanstalk',
                newTemplateFileName='config.yml',
            )
        except Exception:
            self.messageClient.send_slack(
                channel=ChannelURL.DEVS,
                message=f'Failed to create application {self.service} with staging and live environments on Elasticbeanstalk',
                colour=Colors.DANGER,
            )
        return self.messageClient.send_slack(
            channel=ChannelURL.DEVS,
            message=f'Application {self.service} with environments {self.service}-staging, {self.service}-live have been created successfully. '
            'Waiting for environments to be in healthy state before creating alias records and deploying on staging',
            colour=Colors.GOOD,
        )

    def env_ready(self, environmentName, timeout, period):
        return utils.wait_until(
            condition=self.orchestratorClient.get_environment_health,
            expected='Green',
            timeout=timeout,
            period=period,
            environmentName=environmentName,
        )

    def create_alias_record(self):
        for environmentName in self.environmentNames:
            environmentType = environmentName.split(sep='-')[1]
            self.liveURL = f'{self.service}.{os.environ.get("DOMAIN_NAME")}'
            if self.env_ready(environmentName=environmentName, timeout=600, period=60):
                self.dnsClient.create_dns_record(
                    hostedZoneId=os.environ.get('HOSTED_ZONE_ID'),
                    resourceRecordSet={
                        'Name': self.liveURL
                        if environmentType == 'live'
                        else f'{environmentType}.{self.liveURL}',
                        'Type': 'A',
                        'AliasTarget': {
                            'HostedZoneId': Route53HostedZoneId.EU_WEST_2,
                            'DNSName': self.orchestratorClient.get_environment_dns(
                                environmentName=environmentName
                            ),
                            'EvaluateTargetHealth': True,
                        },
                    },
                )

    def deploy(self):
        timeout = 600
        if self.env_ready(
            environmentName=self.environmentNames[0], timeout=timeout, period=60
        ):
            subprocess.check_call(
                [
                    'python',
                    'deploy.py',
                    '--service',
                    self.repoName,
                    '--env',
                    self.environmentNames[0],
                    '--auto',
                ]
            )
        else:
            raise SystemExit(
                f'Environment {self.environmentNames[0]} is not ready after waiting {timeout} seconds.'
                'Check directly environment health and try later.'
            )
        return self.messageClient.send_slack(
            channel=ChannelURL.DEVS,
            message=f'Service {self.service} is now accessible at staging.{self.liveURL}.',
            colour=Colors.GOOD,
        )

    def run(self, createRepo, template, environment):
        self.repoName = self.service.capitalize()
        self.user = (
            subprocess.check_output(['git', 'config', '--get', 'user.name'])
            .decode()
            .strip()
        )
        if createRepo:
            self.create_repo()
        self.generate_ssh_key()
        self.add_ssh_key_to_repo()
        if createRepo:
            self.pull_repo()
        self.clean_ssh_repo()
        self.update_git_config()
        if createRepo:
            self.set_default_branch()
            self.create_build()
            self.create_webhook()
            self.create_build_notification()
            self.add_template(template=template)
            self.trigger_build()
            self.add_branch_protection_rules()
        if environment:
            self.host_service()
            self.create_alias_record()
            self.deploy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Creation service tool')
    parser.add_argument('--service', type=str, nargs=1, help='service name')
    parser.add_argument(
        '--framework',
        type=str,
        nargs=1,
        help='for gitignore and skeleton templates (ex: react, fast_api)',
    )
    parser.add_argument(
        '--no-repo',
        action='store_false',
        dest='createRepo',
        help="Add this flag if we don't need to create a service but just to set/reset SSH keys for a service",
    )
    parser.set_defaults(createRepo=True)
    parser.add_argument(
        '--no-template',
        action='store_false',
        dest='template',
        help="Add this flag if we don't need to create a skeleton from an existing template (fast_api, react templates...)",
    )
    parser.set_defaults(template=True)
    parser.add_argument(
        '--environment',
        action='store_true',
        dest='environment',
        help="Add this flag if we want to create an application with environments staging and live",
    )
    parser.set_defaults(environment=False)
    args = parser.parse_args()

    service = args.service[0].lower()
    framework = args.framework[0].lower()
    organisation = os.environ.get('ORGANISATION')
    token = os.environ.get('GITHUB_TOKEN')
    user = os.environ.get('USER')
    repoManagerClient = GithubClient(token=token)
    messageClient = SlackClient()
    continuousIntegrationClient = CodeBuildClient(service=service)
    notificationClient = CodeStarClient()
    orchestratorClient = ElasticBeanstalkClient()
    dnsClient = Route53Client()
    serviceCreator = ServiceCreator(
        user=user,
        organisation=organisation,
        service=service,
        framework=framework,
        repoManagerClient=repoManagerClient,
        messageClient=messageClient,
        continuousIntegrationClient=continuousIntegrationClient,
        notificationClient=notificationClient,
        orchestratorClient=orchestratorClient,
        dnsClient=dnsClient,
    )

    serviceCreator.run(
        createRepo=args.createRepo, template=args.template, environment=args.environment
    )
