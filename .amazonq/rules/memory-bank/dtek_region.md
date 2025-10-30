## DTEK Region API

### Data Source
- URL: https://www.dtek-krem.com.ua/ua/shutdowns
- Protected by Incapsula - requires curl-cffi with Chrome impersonation
- Data embedded in HTML as `DisconSchedule.fact` JavaScript object
  ```html
  <html><body><script>
  DisconSchedule.currentWeekDayIndex = 3
  DisconSchedule.fact = {"data":{"1761688800":{"GPV1.1":{"1":"yes","2":"yes","3":"yes","4":"yes","5":"yes","6":"yes","7":"yes","8":"yes","9":"yes","10":"yes","11":"yes","12":"yes","13":"second","14":"no","15":"no","16":"no","17":"first","18":"yes","19":"yes","20":"yes","21":"yes","22":"yes","23":"yes","24":"yes"},"GPV1.2":{...}}},"update":"29.10.2025 13:51","today":1761688800}</script><script type="text/javascript" src="/_Incapsula_Resource?ABC=123&ns=1&cb=123" async></script></body>
  </html>
  ```
- Extract using regex: `DisconSchedule\.fact\s*=\s*({.*?})</script>`

### Data Structure
```json
{
  "data": {
    "1761688800": {  // Unix timestamp (UTC)
      "GPV1.1": {"1": "yes", "13": "second", "14": "no", "17": "first", ...},
      "GPV1.2": {...}
    },
    "1761775200": {...}
  },
  "update": "29.10.2025 13:51",  // DD.MM.YYYY HH:MM format
  "today": 1761688800
}
```

### Hour Status Values
- `"yes"` - no outage
- `"no"` - full hour outage
- `"second"` - outage in SECOND 30 minutes (hour:30 to hour+1:00) (usually this is the starting block of a range)
- `"first"` - outage in FIRST 30 minutes (hour:00 to hour:30) (usually this is the ending block of a range)

### Outage Patterns (Production)
1. All "yes" - no outages
2. All "no" - full day outage
3. Consecutive "no" blocks
4. "second" + "no"* + "first" blocks (merged ranges)
5. "second" + "first"

**Key insight**: "first" and "second" ONLY appear at boundaries, never isolated.

### Parsing Logic
- "first"/"no"/"second" are all outages
- "second" starts at hour:30
- "first" starts at hour:00 and ALWAYS closes at hour:30
- "no" continues existing outage
- "yes" ends any outage

### Example
```
'13': 'second' → outage 12:30-13:00
'14': 'no'     → continues 13:00-14:00
'15': 'no'     → continues 14:00-15:00
'16': 'no'     → continues 15:00-16:00
'17': 'first'  → continues 16:00-16:30, then closes
'18': 'yes'    → no outage
Result: single range (12:30, 16:30)
```

### Implementation
- Module: `custom_components/svitlo_yeah/api/dtek_regions.py`
- Class: `DtekRegionAPI`
- Methods: `fetch_data()`, `get_groups()`, `get_updated_on()`, `get_events()`, `_parse_group_hours()`
