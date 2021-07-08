import boto3
import json
import os

import urllib.request
import urllib.parse


def listHostsZones():
    '''
    Fetches all the hostedzones and returns a JSON
    object with format {"domain.tld": "zoneId"}
    '''

    hostIds = {}

    command = '/opt/aws route53 list-hosted-zones'
    hostedZones = json.loads(os.popen(command).read())
    zones = hostedZones['HostedZones']

    for records in zones:
        host = records['Name']
        hostId = records['Id']

        hostIds[host] = hostId
    
    return(hostIds)


def parseHostsZone(hostedZones):
    '''
    Beautify and print the hostedzones -> domains
    '''

    count = 1

    for key, vals in zip(hostedZones.keys(), hostedZones.values()):
        print(f"[{count}]\t{key}")
        count += 1


def getZoneDetails(hostName, hostId, jsonOutput=False):
    '''
    Get the DNS records of the specified hostName or
    hosted zone and find and return all CNAME records
    within it
    '''

    results = {}

    command = f'/opt/aws route53 list-resource-record-sets --hosted-zone-id {hostId}'
    zoneRecords = json.loads(os.popen(command).read())['ResourceRecordSets']

    for dnsRecords in zoneRecords:
        recordType = dnsRecords['Type']
        recordName = dnsRecords['Name']

        if 'ResourceRecords' in dnsRecords:
            recordValue = dnsRecords['ResourceRecords']

        elif 'AliasTarget' in dnsRecords:
            recordValue = dnsRecords['AliasTarget']

        if recordType == 'CNAME':
            for vals in recordValue:
                if 'Value' in vals:
                    if "This resource record set includes an attribute that is unsupported" in vals['Value']:
                        results[recordName] = 'None'

                    else:
                        results[recordName] = vals['Value']

            if 'DNSName' in recordValue:
                results[recordName] = recordValue['DNSName']

    results = json.dumps(results, default=str, indent=4)
    return(results)


def parseElasticBeanStalkInstances(jsonBlob, region):
    '''
    Parses the results to remove bogus DNS records and
    returns two lists containing subdomains and records
    '''

    subd = []
    rec = []

    jsonBlob = json.loads(jsonBlob)

    for subdomain, dnsRecord in zip(jsonBlob.keys(), jsonBlob.values()):
        if ".elasticbeanstalk." in dnsRecord:
            if region in dnsRecord:
                record = dnsRecord.split(".")
                record = [x for x in record if x] # Remove spaces

                if record[::-1][1] == 'elasticbeanstalk':
                    if len(record) != 5:
                        record = ".".join(record)

                        rec.append(record)
                        subd.append(subdomain)

    return(subd, rec)


def createElasticBeanStalkClient():
    '''
    Boto3 client call required prior to do any
    other API calls
    '''

    return boto3.client('elasticbeanstalk')


def checkElasticBeanStalkTakeover(eBeanStalkClientCall, subdomain, record):
    '''
    Does check_dns_availability(
        CNAMEPrefix = appName
    )

    against the specified application and checks if 
    we can take over the application name
    '''

    post = ''
    appName = record.split(".")[0]

    response = eBeanStalkClientCall.check_dns_availability(
        CNAMEPrefix = appName
    )

    jsonData = json.loads( json.dumps(response, default=str) )
    available = jsonData.get('Available')
    fqCNAME = jsonData.get('FullyQualifiedCNAME')

    if available == True:
        print(f"{subdomain}, 'CanTakeOver', {record}")
        post += f"- {subdomain} - {record}\n"

    else:
        print(f"{subdomain}, {available}, {record}")

    return(post)


def webHookPost(webhook, data):
    '''
    Function to post to Slack data, takes in the 
    webhook url and the data to post
    '''

    data = json.dumps({'text': data}).encode('utf-8')
    req  = urllib.request.Request(webhook, data, {'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    response = resp.read()


def lambda_handler(event, context):
    print('Listing hosted zones\n')
    
    hostedZones     = listHostsZones()
    parsedResults   = parseHostsZone(hostedZones)

    webhook = os.getenv('WEBHOOK_URL')
    region = os.getenv('REGION')

    for hostName, hostId in zip(hostedZones.keys(), hostedZones.values()):
        print(f"{hostName}\n")
        zoneDetails = getZoneDetails(hostName, hostId, False)

        slackPost = f"\n*Host: `{hostName}`*\n\n"
        print("Checking ElasticBeanStalk takeoverable instances")

        if region:
            subd, rec = parseElasticBeanStalkInstances(zoneDetails, region)

        else:
            subd, rec = parseElasticBeanStalkInstances(zoneDetails, 'eu-west-1')


        clientCall = createElasticBeanStalkClient()

        for subdomains, records in zip(subd, rec):
            slackPost += checkElasticBeanStalkTakeover(clientCall, subdomains, records)

        if webhook: webHookPost(webhook, slackPost)