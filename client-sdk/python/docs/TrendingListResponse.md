# TrendingListResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**terms** | [**List[TrendingTermResponse]**](TrendingTermResponse.md) | List of trending terms | [optional]
**total_count** | **int** | Total number of trending terms | [optional]
**last_updated** | **datetime** | When the trending data was last updated |
**category_filter** | **str** | Applied category filter | [optional]

## Example

```python
from lingible_client.models.trending_list_response import TrendingListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of TrendingListResponse from a JSON string
trending_list_response_instance = TrendingListResponse.from_json(json)
# print the JSON string representation of the object
print(TrendingListResponse.to_json())

# convert the object into a dict
trending_list_response_dict = trending_list_response_instance.to_dict()
# create an instance of TrendingListResponse from a dict
trending_list_response_from_dict = TrendingListResponse.from_dict(trending_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
