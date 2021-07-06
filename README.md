# Route53 - Subdomains takeover

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/cloudposse.svg?style=social&label=%40syed_umar)](https://twitter.com/syed__umar)

[contributors-shield]: https://img.shields.io/github/contributors/Anon-Exploiter/Route53-SubdomainsTakeover.svg?style=flat-square
[contributors-url]: https://github.com/Anon-Exploiter/Route53-SubdomainsTakeover/graphs/contributors
[issues-shield]: https://img.shields.io/github/issues/Anon-Exploiter/Route53-SubdomainsTakeover.svg?style=flat-square
[issues-url]: https://github.com/Anon-Exploiter/Route53-SubdomainsTakeover/issues

A script to fetch all route53 hosted zones, fetch all CNAME DNS records of each zone (domain) then check all the records containing elasticbeanstalk applications -- **if they're takeoverable** -- and post all that on Slack!  

***Readme's kinda not updated since the script is under development**

### Tested On (OS & Python version)
- WSL2 - Ubuntu 20.04 LTS -- Python 3.8.5

### Downloading & Installation
```bash
git clone https://github.com/Anon-Exploiter/Route53-SubdomainsTakeover
cd Route53-SubdomainsTakeover/
python3 -m venv env && source env/bin/activate # Create virtualenv to install packages in
pip install -r requirements.txt

python3 route53Records.py
```

### Why?

Wrote this for a client they had over **1000+ elasticbeanstalk applications** and then Route53 DNS records pointing to them - **Almost 90% were stale** and some **subdomains were publicly foundable/dorkable**. 

This will help me in giving them all the results to work with -- and to what to remove and what to not! 

### Usage

Help menu

```csharp
$ python3 route53Records.py --help
[#] Usage: python3 route53Records.py --all

Basic Help:
  -h, --help            show this help message and exit

Arguments:
  -r REGION, --region REGION
                        Specify region (default: eu-west-1)
  -l, --list            List all hosted zones with Ids
  -f FETCH, --fetch FETCH
                        Fetch select zones and records
  -a, --all             Get all the zones and their records
```

Listing all the domains (hosted zones) present in the AWS account

```csharp
$ python3 route53Records.py --list

-------------------------------------------------------
               Listing hosted zones ...
-------------------------------------------------------

[1]     test1.com.
[2]     test2.com.
```

Fetching results of specific hosted zones (*id* from *--list*)

```csharp
$ python3 route53Records.py --fetch 1

-------------------------------------------------------
               Listing hosted zones ...
-------------------------------------------------------

[1]     test1.com.
[2]     test2.com.


----------------------------------------------
                test1.com. ...
----------------------------------------------
{
    "subdomain1.test1.com.": "subdomain1.us-east-1.elasticbeanstalk.com",
    "subdomain2.test1.com.": "subdomain2.us-east-1.elasticbeanstalk.com",
    "subdomain3.test1.com.": "subdomain3.us-east-1.elasticbeanstalk.com",
    ...
}

-----------------------------------------------------------------------------------
               Checking ElasticBeanStalk takeoverable instances ...
-----------------------------------------------------------------------------------

[!]  subdomain1.test1.com., 'CanTakeOver', subdomain1.us-east-1.elasticbeanstalk.com
[!]  subdomain2.test1.com., False, subdomain2.us-east-1.elasticbeanstalk.com
[!]  subdomain3.test1.com., 'CanTakeOver', subdomain3.us-east-1.elasticbeanstalk.com
```

In the above case **subdomain1** and **subdomain2** are takeoverable!

### Todos
- <s>Add region check (what region are we in?)</s>
- <s>Add Slack alerting</s> <small>[5b6d279](https://github.com/Anon-Exploiter/Route53-SubdomainsTakeover/commit/5b6d27918079af709d58f29400be4591c5c3238e)</small> covers it
- Create a Docker image of the script
- Integrate Static hosting S3 bucket takeover check
- Integrate other open-source subdomain takeover check scripts
- Do more QA testing

### Filing Bugs/Contribution
Feel free to file a issue or create a PR for that issue if you come across any.
