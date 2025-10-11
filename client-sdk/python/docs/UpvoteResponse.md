# UpvoteResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**submission_id** | **str** | The upvoted submission ID |
**upvotes** | **int** | Total upvote count after this upvote |
**message** | **str** | Success message |

## Example

```python
from lingible_client.models.upvote_response import UpvoteResponse

# TODO update the JSON string below
json = "{}"
# create an instance of UpvoteResponse from a JSON string
upvote_response_instance = UpvoteResponse.from_json(json)
# print the JSON string representation of the object
print(UpvoteResponse.to_json())

# convert the object into a dict
upvote_response_dict = upvote_response_instance.to_dict()
# create an instance of UpvoteResponse from a dict
upvote_response_from_dict = UpvoteResponse.from_dict(upvote_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
