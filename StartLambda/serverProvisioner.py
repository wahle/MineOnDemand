# -*- coding: utf-8 -*-
import time
import os
import boto3
import paramiko


def lambda_handler(event, context):
    #Pull From Environment Vars
    instanceID = os.getenv("InstanceID")
    region = os.getenv("Region")

    ec2 = boto3.client('ec2', region_name=region)
    instance_id = [instanceID]

    # Start the instance
    startResponse = ec2.start_instances(InstanceIds = instance_id)

    # Check for successful start
    stateCode = 0
    while not (stateCode == 16):
        time.sleep(3)

        print('\nAWS EC2 START RESPONSE\n')
        print(str(startResponse))
        print('\n')

        startResponse = ec2.describe_instances(InstanceIds = instance_id)
        reservations = startResponse['Reservations']
        reservation = reservations[0]

        instances = reservation['Instances']
        instance = instances[0]

        state = instance['State']
        stateCode = state['Code']
        
        print("\nSERVER INSTANCES\n")
        print(instances)
        print("\n")

