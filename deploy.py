import argparse
import os
import subprocess

import requests

from aws_manager import CodeBuildClient
from messaging_manager import ChannelURL, Colors, SlackClient
from models import BColors


class Deploy:
    def __init__(self, service, messageClient, continuousIntegrationClient):
        self.service = service
        self.messageClient = messageClient
        self.continuousIntegrationClient = continuousIntegrationClient

    def use_shell(self):
        return os.name == 'nt'

    def get_new_line(self):
        if self.use_shell():
            return '\r\n'
        else:
            return '\n'

    def run_command(self, *args):
        try:
            return (
                subprocess.check_output(
                    args=args,
                    stderr=subprocess.STDOUT,
                    shell=self.use_shell(),
                    cwd=f'../{self.service}',
                )
                .decode()
                .strip()
            )
        except subprocess.CalledProcessError:
            raise SystemExit(
                f'Error: Could not go to service {service} and execute the command, are you sure the service exists or is in WhatsTheFilms folder?'
            )

    def get_environments(self):
        try:
            envs = self.run_command('eb', 'list')
        except subprocess.CalledProcessError:
            raise SystemExit(
                'Error: Could not read environments from EB, have you run the "aws configure" and "eb init" commands?'
            )
        return [x.lstrip('* ') for x in envs.split(self.get_new_line())]

    def get_current_branch(self):
        return self.run_command('git', 'rev-parse', '--abbrev-ref', 'HEAD')

    def get_current_user(self):
        try:
            return self.run_command('git', 'config', '--get', 'user.name')
        except subprocess.CalledProcessError:
            raise SystemExit(
                'Error: Could not read user name from git, have you set config for user name?'
            )

    def load_context(self):
        self.branch = self.get_current_branch()
        self.branchNoSlashes = self.branch.replace('/', '-')
        print(f'Current branch: {BColors.WARNING}{self.branch}{BColors.ENDC}')
        self.user = self.get_current_user()
        print('Current user', self.user)

    def check_for_dependencies(self):
        try:
            version = self.run_command('eb', '--version')
        except subprocess.CalledProcessError:
            raise SystemExit('Error: Could not find the EB command')
        print(f'Found EB tools: {version}')
        try:
            version = self.run_command('git', '--version')
        except subprocess.CalledProcessError:
            raise SystemExit('Error: Could not find the Git command')
        print(f'Found Git tools: {version}')
        try:
            version = self.run_command('aws', '--version')
        except subprocess.CalledProcessError:
            raise SystemExit('Error: Could not find the aws command')
        print(f'Found aws tools: {version}')

    def check_environment(self, env):
        envs = self.get_environments()
        self.environment = env
        if self.environment not in envs:
            raise SystemExit(
                f'Error: Unknown environment, choose from {", ".join(envs)}'
            )

    def check_live_environment_protection(self):
        if (
            self.environment == f'{self.service.lower()}-live'
            and self.branch != 'master'
        ):
            raise SystemExit(
                'Error: Only the master branch may be deployed to the live environment'
            )

    def check_clean_repo(self):
        output = self.run_command('git', 'status', '--porcelain')
        if output:
            raise SystemExit(
                'Error: Git repo is not clean, new or modified files exist'
            )

    def check_up_to_date(self):
        self.run_command('git', 'remote', 'update')
        self.localHash = self.run_command('git', 'rev-parse', self.branch)

        try:
            remoteHash = self.run_command('git', 'rev-parse', f'origin/{self.branch}')
        except subprocess.CalledProcessError:
            raise SystemExit(
                'Error: Could not find the hash for the remote branch, have you pushed your changes?'
            )

        if self.localHash != remoteHash:
            raise SystemExit(
                f'Error: Local and remote versions of the {self.branch} branch do not match, have you pushed your changes?'
            )

        try:
            commitShas = self.continuousIntegrationClient.get_source_versions()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise SystemExit(
                'Error: failed to get builds information from AWS CodeBuild, connection issue or timeout'
            )
        except requests.exceptions.HTTPError as e:
            raise SystemExit(
                f'Error: failed to get builds information from AWS CodeBuild, error response to HTTP request ({e})'
            )

        if self.localHash not in commitShas:
            raise SystemExit(
                'Error: commit hash for CodeBuild build does not match in the hashes list, '
                f'expected to find: {self.localHash}'
            )

        state = self.continuousIntegrationClient.get_status_for_source_version(
            sourceVersion=self.localHash
        )
        if state != 'SUCCEEDED':
            raise SystemExit(
                'Error: state for CodeBuild build does not match, '
                f'expected: "SUCCEEDED", found: "{state}"'
            )

    def generate_label(self):
        shortHashAndTime = self.run_command(
            'git', 'log', '-1', '--format=%h-%cd', '--date=format:%Y%m%d%H%M%S'
        )
        self.label = f'{self.branchNoSlashes}-{shortHashAndTime}'

    def check_user_confirmation(self):
        print(
            f'You are going to deploy {BColors.WARNING}{self.branch}{BColors.ENDC} to the {BColors.OKGREEN}{self.environment}{BColors.ENDC} '
            f'environment with label {self.label}'
        )
        while True:
            print('Are you sure you want to continue (y/n) => ', end='')
            response = input().lower()
            if response == 'n':
                raise SystemExit('Deploy process exited on user request')
            if response == 'y':
                break
            print('Unrecognised answer, please enter "y" or "n"')

    def do_deployment(self):
        print('Starting deployment process')

        try:
            print('Setting the correct EB environment for deploy')
            self.run_command('eb', 'use', self.environment)
        except subprocess.CalledProcessError:
            raise SystemExit(
                'Error: unable to set the correct EB environment, aborting'
            )

        self.messageClient.send_slack(
            channel=ChannelURL.DEVS,
            message=f'{self.user} has begun the deployment of {self.branch} to the '
            f'{self.environment} environment with label {self.label}',
            colour=Colors.WARNING,
        )

        try:
            print('Running the deploy command')
            subprocess.check_call(
                ['eb', 'deploy', '-l', self.label, '--timeout', '1200'],
                cwd=f'../{self.service}',
            )
        except subprocess.CalledProcessError:
            self.messageClient.send_slack(
                channel=ChannelURL.DEVS,
                message=f'Deployment of {self.branch} to the {self.environment} environment with label '
                f'{self.label} ended with error status, check the deployment status directly',
                colour=Colors.DANGER,
            )
            raise SystemExit(
                'Error: deploy command exited with an error code, check the deployment status directly'
            )

        self.messageClient.send_slack(
            channel=ChannelURL.DEVS,
            message=f'Deployment of {self.branch} to the {self.environment} environment with label '
            f'{self.label} completed successfully',
            colour=Colors.GOOD,
        )
        print('Deployment completed successfully')

    def run(self, env, isAutoDeployment):
        self.use_shell()
        self.check_for_dependencies()
        self.check_environment(env=env)
        self.load_context()
        self.check_live_environment_protection()
        self.check_clean_repo()
        self.check_up_to_date()
        self.generate_label()
        if not isAutoDeployment:
            self.check_user_confirmation()
        self.do_deployment()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Deployment Tool')
    parser.add_argument('--service', type=str, nargs=1, help='service name')
    parser.add_argument('--env', type=str, nargs=1, help='environment name')
    parser.add_argument('--auto', action='store_true')
    args = parser.parse_args()

    service = args.service[0]
    messageClient = SlackClient()
    continuousIntegrationClient = CodeBuildClient(service=service.lower())
    deploy = Deploy(
        service=service,
        messageClient=messageClient,
        continuousIntegrationClient=continuousIntegrationClient,
    )
    deploy.run(env=args.env[0], isAutoDeployment=args.auto)
