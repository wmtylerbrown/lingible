# AdminApprovalResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**submission_id** | **str** | The submission ID |
**status** | **str** | Updated submission status |
**message** | **str** | Success message |

## Example

```python
from lingible_client.models.admin_approval_response import AdminApprovalResponse

# TODO update the JSON string below
json = "{}"
# create an instance of AdminApprovalResponse from a JSON string
admin_approval_response_instance = AdminApprovalResponse.from_json(json)
# print the JSON string representation of the object
print(AdminApprovalResponse.to_json())

# convert the object into a dict
admin_approval_response_dict = admin_approval_response_instance.to_dict()
# create an instance of AdminApprovalResponse from a dict
admin_approval_response_from_dict = AdminApprovalResponse.from_dict(admin_approval_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
