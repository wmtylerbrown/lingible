# UserProfileResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**user_id** | **str** |  |
**email** | **str** |  |
**username** | **str** | Cognito username |
**tier** | **str** |  |
**status** | **str** |  |
**created_at** | **datetime** | Account creation date |
**updated_at** | **datetime** | Last update date | [optional]

## Example

```python
from lingible_client.models.user_profile_response import UserProfileResponse

# TODO update the JSON string below
json = "{}"
# create an instance of UserProfileResponse from a JSON string
user_profile_response_instance = UserProfileResponse.from_json(json)
# print the JSON string representation of the object
print(UserProfileResponse.to_json())

# convert the object into a dict
user_profile_response_dict = user_profile_response_instance.to_dict()
# create an instance of UserProfileResponse from a dict
user_profile_response_from_dict = UserProfileResponse.from_dict(user_profile_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
