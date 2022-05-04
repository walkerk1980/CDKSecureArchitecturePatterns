import aws_cdk as core
import aws_cdk.assertions as assertions

from three_tier_linux.three_tier_linux_stack import ThreeTierLinuxStack

# example tests. To run these tests, uncomment this file along with the example
# resource in three_tier_linux/three_tier_linux_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ThreeTierLinuxStack(app, "three-tier-linux")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
