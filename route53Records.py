from pygments import highlight, lexers, formatters
from utils import *
from sys import argv

import argparse
import json
import os
import boto3

import urllib.request
import urllib.parse


PROCESSES   = 10


def listHostsZones():
    '''
    Fetches all the hostedzones and returns a JSON
    object with format {"domain.tld": "zoneId"}
    '''

    hostIds = {}

    command = 'aws route53 list-hosted-zones'
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
        write(var=None, color=c, data=f"[{count}]\t{g}{key}")
        count += 1


def getZoneDetails(hostName, hostId, jsonOutput=False):
    '''
    Get the DNS records of the specified hostName or
    hosted zone and find and return all CNAME records
    within it
    '''

    results = {}

    command = f'aws route53 list-resource-record-sets --hosted-zone-id {hostId}'
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
    print(highlight(results, lexers.JsonLexer(), formatters.TerminalFormatter()))

    if jsonOutput:
        fileName = ".".join(hostName.split(".")[:-1])
        with open(f'{fileName}.json', 'w+') as f:
            f.write(results)

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
        write(var=f'{r}!', color=r, data=f"{c}{subdomain}{w}, {r}'CanTakeOver'{w}, {y}{record}")
        post += f"- {subdomain} - {record}\n"

    else:
        write(var='#', color=g, data=f"{c}{subdomain}{w}, {g}{available}{w}, {y}{record}")

    return(post)


def addArguments():
    '''
    Args
    '''

    parser = argparse.ArgumentParser(description='', usage=f'\r[#] Usage: python3 {argv[0]} --all')
    parser._optionals.title = "Basic Help"

    opts = parser.add_argument_group(f'Script Arguments')
    opts.add_argument('-l', '--list',     action="store_true", dest="list",     default=False, help='List all hosted zones with Ids')
    opts.add_argument('-f', '--fetch',    action="store",      dest="fetch",    default=False, help='Fetch select zones and records')
    opts.add_argument('-a', '--all',      action="store_true", dest="all",      default=False, help='Get all the zones and their records')

    others = parser.add_argument_group(f'Optional Arguments')
    others.add_argument('-r', '--region',  action="store",      dest="region",  default=False, help='Specify region (default: eu-west-1)')
    others.add_argument('-w', '--webhook', action="store",      dest="webhook", default=False, help='Slack Webhook URL to post to')
    others.add_argument('-j', '--json',    action="store_true", dest="json",    default=False, help='Output route53 CNAME records in JSON')
    others.add_argument('-c', '--csv',     action="store_true", dest="csv",     default=False, help='Output the vulnerable subdomains and records in CSV files')

    args = parser.parse_args()
    return(args, parser)


def webHookPost(webhook, data):
    '''
    Function to post to Slack data, takes in the 
    webhook url and the data to post
    '''

    data = json.dumps({'text': data}).encode('utf-8')
    req  = urllib.request.Request(webhook, data, {'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    response = resp.read()


def formatSlackPostToCSV(post):
    '''
    Convers the Slack Post formatted into CSV
    to write to domain.tld.csv
    '''

    return post.replace(' - ', ',').replace('- ', '')


def main():
    args, parser = addArguments()

    if args.list:
        heading(heading='Listing hosted zones', color=y, afterWebHead='')
        hostedZones     = listHostsZones()
        parsedResults   = parseHostsZone(hostedZones)


    elif args.fetch:
        heading(heading='Listing hosted zones', color=y, afterWebHead='')
        hostedZones     = listHostsZones()

        parsedResults   = parseHostsZone(hostedZones)
        print()

        for hostName, hostId in zip(hostedZones.keys(), hostedZones.values()):
            userInp     = list(hostedZones)[ int(args.fetch) - 1 ]

            if hostName == userInp:
                heading(heading=hostName, color=m, afterWebHead='')
                zoneDetails = getZoneDetails(hostName, hostId, args.json)

                if args.webhook: 
                    slackPost = f"\n*Host: `{hostName}`*\n\n"
                    _slack = ''

                if args.csv:
                    csvData = ''
                    with open(f'{hostName}csv', 'w+') as f: f.write('Subdomain,CNAME record\n')

                heading(heading="Checking ElasticBeanStalk takeoverable instances", color=r, afterWebHead='')

                if args.region:
                    subd, rec = parseElasticBeanStalkInstances(zoneDetails, args.region)

                else:
                    subd, rec = parseElasticBeanStalkInstances(zoneDetails, 'eu-west-1')

                clientCall = createElasticBeanStalkClient()

                if args.webhook:
                    for subdomains, records in zip(subd, rec):
                        _slack += checkElasticBeanStalkTakeover(clientCall, subdomains, records)

                    if args.csv:
                        with open(f'{hostName}csv', 'a+') as f: f.write(formatSlackPostToCSV(_slack))

                    slackPost += _slack
                    webHookPost(args.webhook, slackPost)

                else:
                    if args.csv:
                        for subdomains, records in zip(subd, rec):
                            csvData += checkElasticBeanStalkTakeover(clientCall, subdomains, records)

                        with open(f'{hostName}csv', 'a+') as f: f.write(formatSlackPostToCSV(csvData))

                    else:
                        for subdomains, records in zip(subd, rec):
                            checkElasticBeanStalkTakeover(clientCall, subdomains, records)


    elif args.all:
        heading(heading='Listing hosted zones', color=y, afterWebHead='')
        
        hostedZones     = listHostsZones()
        parsedResults   = parseHostsZone(hostedZones)

        for hostName, hostId in zip(hostedZones.keys(), hostedZones.values()):
            heading(heading=hostName, color=m, afterWebHead='')
            zoneDetails = getZoneDetails(hostName, hostId, args.json)

            if args.webhook: 
                slackPost = f"\n*Host: `{hostName}`*\n\n"
                _slack = ''

            if args.csv:
                csvData = ''
                with open(f'{hostName}csv', 'w+') as f: f.write('Subdomain,CNAME record\n')

            heading(heading="Checking ElasticBeanStalk takeoverable instances", color=r, afterWebHead='')

            if args.region:
                subd, rec = parseElasticBeanStalkInstances(zoneDetails, args.region)

            else:
                subd, rec = parseElasticBeanStalkInstances(zoneDetails, 'eu-west-1')

            clientCall = createElasticBeanStalkClient()

            if args.webhook:
                for subdomains, records in zip(subd, rec):
                    _slack += checkElasticBeanStalkTakeover(clientCall, subdomains, records)

                if args.csv:
                    with open(f'{hostName}csv', 'a+') as f: f.write(formatSlackPostToCSV(_slack))

                slackPost += _slack
                webHookPost(args.webhook, slackPost)

            else:
                if args.csv:
                    for subdomains, records in zip(subd, rec):
                        csvData += checkElasticBeanStalkTakeover(clientCall, subdomains, records)

                    with open(f'{hostName}csv', 'a+') as f: f.write(formatSlackPostToCSV(csvData))

                else:
                    for subdomains, records in zip(subd, rec):
                        checkElasticBeanStalkTakeover(clientCall, subdomains, records)


    else:
    	parser.print_help()
    	exit()


if __name__ == '__main__':
    main()