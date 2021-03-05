import boto3


class Route53Client:
    def __init__(self):
        self.client = boto3.client('route53')

    def create_dns_record(self, hostedZoneId, resourceRecordSet):
        return self.client.change_resource_record_sets(
            HostedZoneId=hostedZoneId,
            ChangeBatch={
                'Changes': [
                    {'Action': 'CREATE', 'ResourceRecordSet': resourceRecordSet},
                ]
            },
        )
