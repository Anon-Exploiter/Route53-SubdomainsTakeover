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


def S3ResourceCall():
    return boto3.resource('s3')


def getBucketNamesFromResults(jsonBlob):
    subds = []
    buckets = []
    recs = []

    isBucket = True
    jsonBlob = json.loads(jsonBlob)

    for subdomain, dnsRecord in zip(jsonBlob.keys(), jsonBlob.values()):
        if "s3-website" in dnsRecord:
            isBucket = False
            results = dnsRecord.split(".s3-website")
            bucketName = results[0]

            subds.append(subdomain)
            buckets.append(bucketName)
            recs.append(dnsRecord)

    if isBucket:
        print('No buckets for this hosts zone..')

    return(subds, buckets, recs)


def checkS3BucketTakeover(s3_resource, subdomain, bucketName, dnsRecords):
    post = ''

    try:
        s3_resource.meta.client.head_bucket(Bucket=bucketName)
        canTakeOver = False
    
    except ClientError as error:
        error_code = int(error.response['Error']['Code'])
        
        if error_code == 403:
            canTakeOver = False
        
        elif error_code == 404:
            canTakeOver = True
    
    if canTakeOver == True:
        print(f"{subdomain}, 'CanTakeOver', {dnsRecords}")
        post += f"• {subdomain} — *`{dnsRecords}`*\n"

    else:
        print(f"{subdomain}, {canTakeOver}, {dnsRecords}")

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
    webhook = os.getenv('WEBHOOK_URL')
    region = os.getenv('REGION')
    
    print('Listing hosted zones\n')
    
    hostedZones = listHostsZones()
    parsedResults = parseHostsZone(hostedZones)

    for hostName, hostId in zip(hostedZones.keys(), hostedZones.values()):
        _slack = ''
        slackPost = f"\n*Following DNS records have been detected to be potentially stale and vulnerable to subdomain takeover for hosted zone: `{hostName}`*\n\n"

        print(f"{hostName}\n")
        zoneDetails = getZoneDetails(hostName, hostId, False)

        print("Checking S3 takeoverable buckets")
        subds, buckets, recs = getBucketNamesFromResults(zoneDetails)

        if len(buckets) != 0:
            s3rsCall = S3ResourceCall()

            for subdomains, bckets, dnsRecords in zip(subds, buckets, recs):
                _slack += checkS3BucketTakeover(s3rsCall, subdomains, bckets, dnsRecords)

        print("Checking ElasticBeanStalk takeoverable instances")

        if region:
            subd, rec = parseElasticBeanStalkInstances(zoneDetails, region)

        else:
            subd, rec = parseElasticBeanStalkInstances(zoneDetails, 'eu-west-1')

        clientCall = createElasticBeanStalkClient()

        for subdomains, records in zip(subd, rec):
            _slack += checkElasticBeanStalkTakeover(clientCall, subdomains, records)

        if len(_slack) != 0:
            slackPost += _slack
            webHookPost(webhook, slackPost)