# Translation Storage Cost Optimization

## 🚨 **Cost Concerns**

Storing every translation in the database can become expensive as usage grows:

- **DynamoDB Storage**: ~$0.25/GB/month
- **Read/Write Operations**: ~$1.25/million requests
- **Example**: 1M translations/month = ~$1.25 + storage costs

## 💡 **Cost Optimization Strategies**

### **1. Selective Storage (Current Implementation)**

Only save translations that meet specific criteria:

```python
# Environment Variables for Configuration
TRANSLATION_STORAGE_STRATEGY=selective  # or "all"
SAVE_ALL_PREMIUM=true                   # Premium users get full history
MIN_CONFIDENCE_THRESHOLD=0.8            # Only save high-confidence translations
MIN_TEXT_LENGTH=50                      # Only save longer text (>50 chars)
RECENT_HOURS_THRESHOLD=24               # Save recent translations (last 24h)
TRANSLATION_TTL_DAYS=365                # Auto-delete after 1 year
ENABLE_DEDUPLICATION=false              # Avoid storing duplicates
```

**Storage Criteria:**
- ✅ Premium users: All translations saved
- ✅ High confidence (>0.8): Save valuable translations
- ✅ Longer text (>50 chars): More valuable content
- ✅ Recent translations (24h): Recent activity
- ❌ Short, low-confidence, old translations: Skip

### **2. TTL (Time-To-Live) Cleanup**

Automatic deletion after configurable period:
- **Default**: 365 days
- **Configurable**: `TRANSLATION_TTL_DAYS` environment variable
- **Cost Impact**: Reduces long-term storage costs

### **3. Alternative Storage Strategies**

#### **Option A: No Storage (Minimal Cost)**
```python
TRANSLATION_STORAGE_STRATEGY=none
```
- ❌ No translation history
- 💰 Minimal database costs
- 🎯 Good for MVP or cost-sensitive deployments

#### **Option B: Premium-Only Storage**
```python
TRANSLATION_STORAGE_STRATEGY=premium_only
SAVE_ALL_PREMIUM=true
```
- ✅ Premium users: Full history
- ❌ Free users: No storage
- 💰 Moderate costs, premium feature

#### **Option C: Aggregated Storage**
Store only metadata, not full text:
```python
TRANSLATION_STORAGE_STRATEGY=aggregated
```
- ✅ Store: translation_id, user_id, direction, confidence, timestamp
- ❌ Don't store: original_text, translated_text
- 💰 Significant cost reduction (~60% less storage)

## 📊 **Cost Comparison**

| Strategy | Storage Cost | Features | Best For |
|----------|-------------|----------|----------|
| **All Translations** | $100/month | Full history | Premium apps |
| **Selective** | $25/month | Smart filtering | Production apps |
| **Premium Only** | $15/month | Premium feature | Freemium apps |
| **Aggregated** | $10/month | Metadata only | Analytics focus |
| **No Storage** | $2/month | No history | MVP/Cost-sensitive |

## 🔧 **Implementation**

### **Current Configuration**
```python
# In translation_service.py
def _should_save_translation(self, response: Translation, user_id: str) -> bool:
    # Premium users get full history
    if self.storage_config["save_all_premium"]:
        user = self.user_service.get_user(user_id)
        if user and user.tier in ["premium", "pro"]:
            return True

    # High confidence translations
    min_confidence = self.storage_config["min_confidence_threshold"]
    if response.confidence_score and response.confidence_score > min_confidence:
        return True

    # Longer text is more valuable
    min_length = self.storage_config["min_text_length"]
    if len(response.original_text) > min_length:
        return True

    # Recent translations
    recent_hours = self.storage_config["recent_hours_threshold"]
    recent_threshold = datetime.now(timezone.utc) - timedelta(hours=recent_hours)
    if response.created_at > recent_threshold:
        return True

    return False  # Don't save to reduce costs
```

### **Monitoring**
```python
# Log when translations are skipped
logger.log_business_event(
    "translation_skipped_storage",
    {
        "translation_id": response.translation_id,
        "user_id": user_id,
        "reason": "cost_optimization",
        "strategy": "selective",
    },
)
```

## 🎯 **Recommendations**

### **For Production Apps:**
1. **Start with Selective Storage** (current implementation)
2. **Monitor costs** and adjust thresholds
3. **Consider Premium-Only** for freemium models
4. **Use TTL** for automatic cleanup

### **For MVP/Cost-Sensitive:**
1. **Use No Storage** strategy
2. **Focus on core functionality**
3. **Add storage later** when needed

### **For Premium Apps:**
1. **Store all translations** for premium users
2. **Use selective storage** for free users
3. **Implement deduplication** to avoid duplicates

## 🔄 **Migration Strategies**

### **From All Storage to Selective:**
1. Set `TRANSLATION_STORAGE_STRATEGY=selective`
2. Monitor skipped translations
3. Adjust thresholds based on user feedback
4. Consider data migration for existing users

### **From Selective to Premium-Only:**
1. Set `SAVE_ALL_PREMIUM=true`
2. Set other criteria to very high thresholds
3. Communicate change to users
4. Offer premium upgrade for history

## 📈 **Future Optimizations**

1. **Deduplication**: Avoid storing identical translations
2. **Compression**: Compress text before storage
3. **Caching**: Use Redis for recent translations
4. **Analytics**: Store only aggregated usage data
5. **User Preferences**: Let users choose storage level
