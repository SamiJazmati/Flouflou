import boto3


class CodeStarClient:
    def __init__(self):
        self.client = boto3.client('codestar-notifications')

    def create_notification_rule(
        self, name, eventTypeIds, resource, targets, detailType, status
    ):
        return self.client.create_notification_rule(
            Name=name,
            EventTypeIds=eventTypeIds,
            Resource=resource,
            Targets=targets,
            DetailType=detailType,
            Status=status,
        )
