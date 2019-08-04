# -*- coding: utf-8 -*-
import time
import os
import boto3
import paramiko


def lambda_handler(event, context):
    if event("serverPassword") == os.getenv("MinePass"):
        ec2 = boto3.client('ec2', region_name=os.getenv("Region"))
        statusMessage = manageServer(ec2)
        print(statusMessage)
        return statusMessage

def manageServer(client):
    serverStatusMessage = 'ERROR unable to interact with server. Please tell someone who cares'
    instance_id = [os.getenv("InstanceID")]

    response = client.describe_instances(InstanceIds = instance_id)
    instances = response.Reservations[0].Instances
    print("\nSERVER INSTANCES\n")
    print(instances)
    print("\n")
    if len(instances) > 0:
        instance = instances[0]
        state = instance['State']
        stateName = state['Name']

        if (stateName == 'stopped') or (stateName == 'shutting-down'):
            #SETUP MULTIPROCESSING HERE INSTEAD OF REDIS
            serverStartMessage = startServer(client)
            #Redirect Route53 to new host
            serverRoutingMessage = route53Redirect(serverStartMessage)
            serverStatusMessage = "Server Successfully Started IP: " + serverStartMessage + serverRoutingMessage
        elif stateName == 'running':
            serverStatusMessage = 'IP: ' + instance['PublicIpAddress']
        else:
            serverStatusMessage = 'ERROR ec2 instance either not found or in a bad state. Needs admin attention.'
    return serverStatusMessage

def startServer(client):
    #Gets proper variables to attempt to instantiate EC2 instance and start minecraft server
    serverStatusMessage = 'ERROR, something went wrong starting ec2.'
    instance_id = [os.getenv("InstanceID")]
    response = client.start_instances(InstanceIds = instance_id)

    stateCode = 0
    while not (stateCode == 16):
        time.sleep(3)

        print('\nAWS EC2 START RESPONSE\n')
        print(str(response))
        print('\n')

        response = client.describe_instances(InstanceIds = instance_id)
        stateCode = response.Reservations[0].Instances[0].State.Code
        
        print("\nSERVER INSTANCES\n")
        print(response.Reservations[0].Instances)
        print("\n")
        
    ipAddress = response.Reservations[0].Instances[0].PublicIpAddress
    serverStatusMessage = ipAddress

    return serverStatusMessage

def route53Redirect(ipAddress):
    serverStatusMessage = 'ERROR, something went wrong updating Route53.'
    dnsClient = boto3.client('route53', region_name=os.getenv("Region"))
    dnsResponse = dnsClient.change_resource_record_sets(
        HostedZoneId=os.getenv('HostedZone'), #"Z3ULH0224N6IL2",
        ChangeBatch={
            "Comment": "Automatic DNS update",
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": os.getenv('DnsName'), # "minecraft.wahl-e.name", 
                        "Type": "A",
                        "TTL": 180,
                        "ResourceRecords": [
                            {
                                "Value": ipAddress
                            },
                        ],
                    }
                },
            ]
        }
    )
    route53UpdateStatus = dnsResponse.ChangeInfo.status
    serverStatusMessage = 'Route53 redirect status:' + route53UpdateStatus

    return serverStatusMessage


