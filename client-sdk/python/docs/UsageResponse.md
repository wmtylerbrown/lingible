# UsageResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**tier** | **str** | User tier | [optional]
**daily_limit** | **int** | Daily translation limit | [optional]
**daily_used** | **int** | Number of translations used today | [optional]
**daily_remaining** | **int** | Number of translations remaining today | [optional]
**reset_date** | **datetime** | Next daily reset date | [optional]
**current_max_text_length** | **int** | Maximum text length for user&#39;s current tier | [optional]
**free_tier_max_length** | **int** | Free tier text length limit | [optional]
**premium_tier_max_length** | **int** | Premium tier text length limit | [optional]
**free_daily_limit** | **int** | Free tier daily translation limit | [optional]
**premium_daily_limit** | **int** | Premium tier daily translation limit | [optional]

## Example

```python
from lingible_client.models.usage_response import UsageResponse

# TODO update the JSON string below
json = "{}"
# create an instance of UsageResponse from a JSON string
usage_response_instance = UsageResponse.from_json(json)
# print the JSON string representation of the object
print(UsageResponse.to_json())

# convert the object into a dict
usage_response_dict = usage_response_instance.to_dict()
# create an instance of UsageResponse from a dict
usage_response_from_dict = UsageResponse.from_dict(usage_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
