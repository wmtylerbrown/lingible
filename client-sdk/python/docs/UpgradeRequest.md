# UpgradeRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**platform** | **str** | App store platform |
**transaction_id** | **str** | Provider transaction ID |
**product_id** | **str** | Product ID from the app store |
**purchase_date** | **datetime** | Purchase date in ISO format |
**expiration_date** | **datetime** | Expiration date in ISO format (for subscriptions) | [optional]
**environment** | **str** | App Store environment |

## Example

```python
from lingible_client.models.upgrade_request import UpgradeRequest

# TODO update the JSON string below
json = "{}"
# create an instance of UpgradeRequest from a JSON string
upgrade_request_instance = UpgradeRequest.from_json(json)
# print the JSON string representation of the object
print(UpgradeRequest.to_json())

# convert the object into a dict
upgrade_request_dict = upgrade_request_instance.to_dict()
# create an instance of UpgradeRequest from a dict
upgrade_request_from_dict = UpgradeRequest.from_dict(upgrade_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
