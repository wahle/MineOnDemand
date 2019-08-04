# -*- coding: utf-8 -*-
import time
import os
import boto3
import paramiko


def lambda_handler(event, context):
    statusMessage = "Wrong Password Given"
    if event["serverPassword"] == os.getenv("MinePass"):
        ec2 = boto3.client('ec2', region_name=os.getenv("Region"))
        statusMessage = manageServer(ec2)
        print(statusMessage)
    return statusMessage

def manageServer(client):
    serverStatusMessage = 'ERROR unable to interact with server. Please tell someone who cares'
    instance_id = [os.getenv("InstanceID")]
    response = client.describe_instances(InstanceIds = instance_id)

    reservations = response['Reservations']
    reservation = reservations[0]
    instances = reservation['Instances']
    
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
            javaServerStatusMessage = "ERROR Game server not started"
            if "Successfully" in serverStatusMessage:
                javaServerStatusMessage = startGameServer(serverStartMessage)
            serverStatusMessage = serverStatusMessage + " " + javaServerStatusMessage
        elif stateName == 'running':
            serverStatusMessage = 'IP: ' + instance['PublicIpAddress']
        else:
            serverStatusMessage = 'ERROR ec2 instance either not found or in a bad state. Needs admin attention. ' + stateName
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
        reservations = response['Reservations']
        reservation = reservations[0]
        instances = reservation['Instances']
        instance = instances[0]
        state = instance['State']
        stateCode = state['Code']

        print("\nSERVER INSTANCES\n")
        print(instances)
        print("\n")
        
    ipAddress = instance['PublicIpAddress']
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
    route53Info = dnsResponse['ChangeInfo']
    route53UpdateStatus = route53Info['Status']
    serverStatusMessage = 'Route53 redirect status:' + route53UpdateStatus
    return serverStatusMessage

def pullFromS3(fileToCopy, bucket):
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket, Key=fileToCopy)
    fileFromS3 = response['Body'].read().decode('utf-8')
    return fileFromS3

def startGameServer(ipAddress):
    sshkey = pullFromS3(os.getenv('serverSshKey'), os.getenv('serverBucket'))
    key = paramiko.RSAKey.from_private_key_file(sshkey)
    sshClient = paramiko.SSHClient()
    sshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect/ssh to an instance
    try:
        # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
        sshClient.connect(hostname=ipAddress, username="ubuntu", pkey=key)

        # Execute a command(cmd) after connecting/ssh to an instance
        #Vanilla Command:
        stdin, stdout, stderr = sshClient.exec_command("screen -dmS minecraft bash -c 'sudo java -Xmx2G -jar server.jar nogui'")
        #Modded Command: 
        # stdin, stdout, stderr = sshClient.exec_command("screen -dmS minecraft bash -c 'sudo java -Xmx4G ${JAVA_ARGS} -jar forge-1.12.2-14.23.5.2836-universal.jar nogui'")
        print("COMMAND EXECUTED")
        # close the client connection once the job is done
        sshClient.close()
        return "Game Client Starting"

    except Exception as e:
        failMessage = "ERROR running Game server commands" + e
        return failMessage
