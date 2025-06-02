from llama_index.core import PromptTemplate

txt_2_diagram_template_str = """
As an AWS Solution Architect, you've been tasked with creating a visual representation of a resilient event processing architecture using Python and the 'diagrams' library. Your goal is to illustrate best practices for error handling in AWS services, focusing on retry mechanisms, dead letter queues, and alerting systems.
Your diagram should showcase the requests specified from user.

### User Query:

I need the following AWS architecture

Amazon EventBridge for scheduling periodic redrives
Amazon SQS for the main queue and dead letter queue (DLQ)
AWS Lambda for event processing
Amazon S3 for storing processed data
Amazon CloudWatch for monitoring
Amazon SNS for alerting
A representation of the development team for manual interventions

Ensure your diagram clearly demonstrates:

The flow of events through the system
How failed events are handled and redirected to the DLQ
The periodic redrive process from DLQ back to the main queue
Monitoring and alerting mechanisms
The role of the development team in updating the Lambda function and receiving alerts

Use Python with the 'diagrams' library to create this architectural diagram. Your code should be clear, well-commented, and showcase AWS best practices for error handling and event processing.
Now please generate the code for the Architecture plan below following the best practices.

### Code

```
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.integration import Eventbridge, SQS
from diagrams.aws.compute import Lambda
from diagrams.aws.storage import S3
from diagrams.aws.management import Cloudwatch
from diagrams.aws.integration import SNS
from diagrams.aws.general import Users
from diagrams.aws.security import Cognito
from diagrams.aws.compute import ECS, ElasticContainerService, EC2ContainerRegistry
from diagrams.aws.network import ELB, VPC, PrivateSubnet, PublicSubnet, InternetGateway, NATGateway

with Diagram("AWS Workflow", show=False, direction="LR", filename="output_diagram"):
    eventbridge = Eventbridge("EventBridge Scheduler")
    
    with Cluster("Queue System"):
        dlq = SQS("DLQ")
        sqs = SQS("SQS Queue")
    
    lambda_func = Lambda("Lambda function")
    s3 = S3("Objects bucket")
    
    with Cluster("Monitoring"):
        cloudwatch = Cloudwatch("Amazon CloudWatch")
        sns = SNS("Amazon SNS")
    
    dev_team = Users("Dev team")

    eventbridge >> Edge(label="periodical\nredrive") >> dlq
    dlq >> Edge(label="redrive") >> sqs
    sqs >> Edge(label="failures") >> dlq
    sqs >> Edge(label="polling\nretries") >> lambda_func
    lambda_func >> s3
    dev_team >> Edge(label="update") >> lambda_func
    dlq >> Edge(label="monitor") >> cloudwatch
    cloudwatch >> Edge(label="alarm") >> sns
    sns >> Edge(label="notify") >> dev_team

print("Diagram has been saved as 'aws_workflow.png'")
```

Now please generate the code for the Architecture plan below following the best practices

### Architecture Plan

{architecture_plan}

Ensure your diagram clearly demonstrates:

The flow of events through the system
How failed events are handled and redirected to the DLQ
The periodic redrive process from DLQ back to the main queue
Monitoring and alerting mechanisms
The role of the development team in updating the Lambda function and receiving alerts

Use Python with the 'diagrams' library to create this architectural diagram. Your code should be clear, well-commented, and showcase AWS best practices for error handling and event processing.

The output file should always be named 'output_diagram'.

Return only the Python code without any additional text or backticks.

### Code

"""

# converts a potato prompt to better prompt
better_aws_prompt_str = """Please rewrite the following prompt into a more refined AWS architecture planning request:
{potato_prompt}
"""

# converts a prompt to postman like request (buggy doesn't work)
convert_postman_prompt_str = """ 
Generate a single-line Postman request that sends the following JSON body: {{"requirements_plan": ""}} with the value {potato_prompt}.
"""

# if there is an import error this prompt fixes it
fix_import_str = " Fix the error below with correct import. \n {error_txt}. Only return the correct code nothing else."

# prompt to generate code
fix_and_write_code_str = """
                    The following Python code has an error:

                    {original_code}

                    The error message is:
                    {error_message}

                    Please fix the code and return only the corrected code without any explanations. 
                    If there are no errors, do nothing.
                    """

# prompt to get pricing
services = [
    "AmazonS3",  # Simple Storage Service
    "AmazonRDS",  # Relational Database Service
    "AmazonCloudFront",  # Content Delivery Network
    "AmazonRoute53",  # Domain Name System (DNS) Web Service
    "AmazonECS",  # Elastic Container Service
    "AmazonSimpleDB",  # NoSQL Database Service
    "AmazonEC2",  # Elastic Compute Cloud
    "AmazonLambda",  # Serverless Compute
    "AmazonDynamoDB",  # NoSQL Database Service
    "AmazonRedshift",  # Data Warehouse Service
    "AmazonSNS",  # Simple Notification Service
    "AmazonSQS",  # Simple Queue Service
    "AWSLambda",  # Lambda Functions
    "AWSGlue",  # Data Integration Service
    "AmazonElasticMapReduce",  # Big Data Processing
    "AWSCloudFormation",  # Infrastructure as Code
    "AWSConfig",  # Resource Inventory and Change Tracking
    "AWSCloudTrail",  # Governance, Compliance, and Operational Auditing
    "AmazonElastiCache",  # In-Memory Caching Service
    "AWSStepFunctions",  # Serverless Workflow Service
    "AmazonEFS",  # Elastic File System
    "AWSBatch",  # Batch Computing Service
    "AmazonKinesis",  # Real-time Data Streaming
    "AmazonCloudWatch",  # Monitoring and Logging Service
    "AmazonAppStream",  # Application Streaming Service
    "AmazonWorkSpaces",  # Virtual Desktop Service
    "AmazonWorkDocs",  # Document Collaboration Service
    "AmazonTranscribe",  # Speech-to-Text Service
    "AmazonComprehend",  # Natural Language Processing Service
    "AmazonLex",  # Conversational Interfaces
    "AmazonRekognition",  # Image and Video Analysis
    "AmazonPolly",  # Text-to-Speech Service
    "AmazonTranslate",  # Language Translation Service
    "AmazonAthena",  # Interactive Query Service
    "AmazonQuickSight",  # Business Intelligence Service
    "AWSDataPipeline",  # Data Workflow Service
    "AWSCodePipeline",  # Continuous Integration and Continuous Delivery
    "AWSCodeBuild",  # Build Service
    "AWSCodeDeploy",  # Deployment Service
    "AWSAppSync",  # GraphQL Service
    "AWSCloud9",  # Cloud IDE
    "AWSIAM",  # Identity and Access Management
    "AWSOrganizations",  # Multi-Account Management
    "AmazonMQ",  # Managed Message Broker Service
    "AmazonChime",  # Communication Service
    "AWSIoTCore",  # Internet of Things Service
    "AWSIoTAnalytics",  # IoT Data Analysis
    "AWSGreengrass",  # IoT Edge Computing
    "AmazonElasticSearch",  # Managed Search Service
    "AmazonSimpleEmailService",  # Email Sending Service
    "AmazonPinpoint",  # User Engagement Service
    "AWSServiceCatalog",  # Cloud Service Catalog
    "AWSWAF",  # Web Application Firewall
    "AWSShield",  # DDoS Protection
    "AWSKeyManagementService",  # Key Management Service
    "AmazonSecretsManager",  # Secrets Management
    "AmazonCertificateManager",  # SSL/TLS Certificate Management
    "AmazonInspector",  # Automated Security Assessment Service
    "AmazonGuardDuty",  # Threat Detection Service
    "AmazonMacie",  # Data Security and Privacy Service
    "AWSElementalMediaConvert",  # Video Transcoding Service
    "AWSElementalMediaPackage",  # Video Packaging and Delivery Service
    "AWSElementalMediaLive",  # Live Video Processing Service
    "AmazonKinesisVideoStreams",  # Video Streaming Service
    "AmazonForecast",  # Time Series Forecasting Service
    "AmazonPersonalize",  # Machine Learning Recommendation Service
    "AmazonSageMaker",  # Machine Learning Service
    "AWSDataBrew",  # Data Preparation Service
    "AmazonAppRunner",  # Application Hosting Service
    "AmazonElasticLoadBalancing",  # Load Balancing Service
    "AWSGlobalAccelerator",  # Network Optimization Service
    "AWSOutposts",  # Hybrid Cloud Service
    "AWSLocalZone",  # Local Compute Resources
    "AWSPrivateLink",  # Private Connectivity to AWS Services
    "AWSMarketplace",  # Digital Marketplace
    "AWSControlTower",  # Governance Service
    "AWSLicenseManager",  # License Management Service
    "AmazonElasticContainerRegistry",  # Docker Container Registry
    "AWSXRay",  # Debugging and Analyzing Microservices
]

services_str = """
You have access to the following AWS services: {', '.join(services)}.

Instructions:
1. Analyze the user's current architecture provided below.
2. Identify and extract the resources used in the architecture.
3. Map each resource to its corresponding AWS service name.
4. Use the mapped service names to call the appropriate AWS pricing API.
"""
pricing_str = """
User's current architecture (using the diagrams library):
{code_txt}

Please provide a detailed breakdown of the resources identified, their mappings to AWS services, and the resulting pricing information.
"""


txt_2_diagram_prompt_template = PromptTemplate(txt_2_diagram_template_str)
better_aws_prompt_template = PromptTemplate(better_aws_prompt_str)
convert_postman_prompt_template = PromptTemplate(convert_postman_prompt_str)
fix_import_prompt_template = PromptTemplate(fix_import_str)
fix_and_write_code_template = PromptTemplate(fix_and_write_code_str)
pricing_prompt_template = PromptTemplate(pricing_str)

# you can create text prompt (for completion API)
# prompt = qa_template.format(architecture_plan="hello world")
# or easily convert to message prompts (for chat API)
# messages = qa_template.format_messages(context_str=..., query_str=...)
