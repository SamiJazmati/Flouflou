import boto3


class CodeBuildClient:
    def __init__(self, service):
        self.client = boto3.client('codebuild')
        self.service = service

    def _get_builds_details(self):
        projectName = f'{self.service}-build'
        ids = self.client.list_builds_for_project(projectName=projectName)['ids']
        buildsDetails = self.client.batch_get_builds(ids=ids)['builds']
        return buildsDetails

    def get_source_versions(self):
        buildsDetails = self._get_builds_details()
        sourceVersions = [
            build['sourceVersion']
            for build in buildsDetails
            if build.get('sourceVersion') is not None
        ]
        return sourceVersions

    def get_status_for_source_version(self, sourceVersion):
        buildsDetails = self._get_builds_details()
        for buildDetail in buildsDetails:
            if buildDetail['sourceVersion'] == sourceVersion:
                return buildDetail['buildStatus']
            else:
                return f'Source Version {sourceVersion} does not exist'

    def create_build(
        self,
        name,
        description,
        source,
        secondarySources,
        secondarySourceVersions,
        artifacts,
        secondaryArtifacts,
        cache,
        environment,
        serviceRole,
        timeoutInMinutes,
        queuedTimeoutInMinutes,
        encryptionKey,
        tags,
        badgeEnabled,
        logsConfig,
    ):
        return self.client.create_project(
            name=name,
            description=description,
            source=source,
            secondarySources=secondarySources,
            secondarySourceVersions=secondarySourceVersions,
            artifacts=artifacts,
            secondaryArtifacts=secondaryArtifacts,
            cache=cache,
            environment=environment,
            serviceRole=serviceRole,
            timeoutInMinutes=timeoutInMinutes,
            queuedTimeoutInMinutes=queuedTimeoutInMinutes,
            encryptionKey=encryptionKey,
            tags=tags,
            badgeEnabled=badgeEnabled,
            logsConfig=logsConfig,
        )

    def create_webhook(self, projectName, filterGroups, buildType):
        return self.client.create_webhook(
            projectName=projectName, filterGroups=filterGroups, buildType=buildType
        )

    def trigger_last_build(self):
        projectName = f'{self.service}-build'.lower()
        return self.client.start_build(projectName=projectName)
