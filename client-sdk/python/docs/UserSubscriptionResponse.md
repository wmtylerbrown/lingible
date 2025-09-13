# UserSubscriptionResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**provider** | **str** | Subscription provider |
**transaction_id** | **str** | Provider transaction ID |
**status** | **str** | Subscription status |
**start_date** | **datetime** | Subscription start date |
**end_date** | **datetime** | Subscription end date | [optional]
**created_at** | **datetime** | Record creation date |

## Example

```python
from lingible_client.models.user_subscription_response import UserSubscriptionResponse

# TODO update the JSON string below
json = "{}"
# create an instance of UserSubscriptionResponse from a JSON string
user_subscription_response_instance = UserSubscriptionResponse.from_json(json)
# print the JSON string representation of the object
print(UserSubscriptionResponse.to_json())

# convert the object into a dict
user_subscription_response_dict = user_subscription_response_instance.to_dict()
# create an instance of UserSubscriptionResponse from a dict
user_subscription_response_from_dict = UserSubscriptionResponse.from_dict(user_subscription_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
