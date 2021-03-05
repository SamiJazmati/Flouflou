import boto3


class ElasticBeanstalkClient:
    def __init__(self):
        self.client = boto3.client('elasticbeanstalk')

    def create_application(self, applicationName, description, tags):
        return self.client.create_application(
            ApplicationName=applicationName, Description=description, Tags=tags
        )

    def create_environment(
        self,
        applicationName,
        environmentName,
        description,
        tier,
        solutionStackName,
        optionSettings,
    ):
        return self.client.create_environment(
            ApplicationName=applicationName,
            EnvironmentName=environmentName,
            Description=description,
            Tier=tier,
            SolutionStackName=solutionStackName,
            OptionSettings=optionSettings,
        )

    def _get_environment_details(self, environmentName):
        return self.client.describe_environments(EnvironmentNames=[environmentName])

    def get_environment_health(self, environmentName):
        response = self._get_environment_details(environmentName=environmentName)
        return response['Environments'][0]['Health']

    def get_environment_dns(self, environmentName):
        response = self._get_environment_details(environmentName=environmentName)
        return response['Environments'][0]['CNAME']
