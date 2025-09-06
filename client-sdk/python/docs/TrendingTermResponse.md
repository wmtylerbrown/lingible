# TrendingTermResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**term** | **str** | The slang term or phrase | [optional] 
**definition** | **str** | Definition or explanation of the term | [optional] 
**category** | **str** | Category of the trending term | [optional] 
**popularity_score** | **float** | Popularity score (0-100) | [optional] 
**search_count** | **int** | Number of times searched | [optional] 
**translation_count** | **int** | Number of times translated | [optional] 
**first_seen** | **datetime** | When this term was first detected | [optional] 
**last_updated** | **datetime** | Last time metrics were updated | [optional] 
**is_active** | **bool** | Whether this term is currently trending | [optional] 
**example_usage** | **str** | Example of how the term is used | [optional] 
**origin** | **str** | Origin or source of the term | [optional] 
**related_terms** | **List[str]** | Related slang terms | [optional] 

## Example

```python
from lingible_client.models.trending_term_response import TrendingTermResponse

# TODO update the JSON string below
json = "{}"
# create an instance of TrendingTermResponse from a JSON string
trending_term_response_instance = TrendingTermResponse.from_json(json)
# print the JSON string representation of the object
print(TrendingTermResponse.to_json())

# convert the object into a dict
trending_term_response_dict = trending_term_response_instance.to_dict()
# create an instance of TrendingTermResponse from a dict
trending_term_response_from_dict = TrendingTermResponse.from_dict(trending_term_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


