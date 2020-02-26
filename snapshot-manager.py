import boto3
import collections
import datetime

ec = boto3.client('ec2')

def lambda_handler(event, context):
    reservations = ec.describe_instances(
        Filters=[
            {'Name': 'tag-key', 'Values': ['ebs-snapshot', 'true']},
        ]
    ).get(
        'Reservations', []
    )

    instances = sum(
        [
            [i for i in r['Instances']]
            for r in reservations
        ], [])

    print("Found %d instances that need backing up" % len(instances))

    for instance in instances:
        try:
            instance_name = [
                t.get('Value') for t in instance['Tags']
                if t['Key'] == 'Name'][0]
            retention_days = [
                int(t.get('Value')) for t in instance['Tags']
                if t['Key'] == 'Retention'][0]
        except IndexError:
            retention_days = 7

        for dev in instance['BlockDeviceMappings']:
            if dev.get('Ebs', None) is None:
                continue
            vol_id = dev['Ebs']['VolumeId']
            print("Found EBS volume %s on instance %s" % (vol_id, instance['InstanceId']))

            current_time = datetime.datetime.utcnow()
            current_time_str = current_time.strftime("%h %d, %H:%M")

            description = "%s Snapshot - created by Grasshopper Snapshot Manager on %s UTC for %s" % (instance_name, current_time_str, instance['InstanceId'])

            delete_date = datetime.date.today() + datetime.timedelta(days=retention_days)
            delete_fmt = delete_date.strftime('%Y-%m-%d')
            tag_spec = [
            	{
            		'ResourceType': 'snapshot',
            		'Tags': [
            			{
            				'Key': 'DeleteOn',
            				'Value': delete_fmt
            			},
            		]
            	},
            ]

            snap = ec.create_snapshot(
                VolumeId=vol_id, Description=description, TagSpecifications=tag_spec
            )

            print("Retaining snapshot %s of volume %s from instance name %s, id %s for %d days" % (
                snap['SnapshotId'],
                vol_id,
                instance_name,
                instance['InstanceId'],
                retention_days
            ))
