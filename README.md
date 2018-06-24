# 4d-plugin-tz
Perform conversion and arithmetic on dates

based on [Time Zone Database Parser](https://howardhinnant.github.io/date/tz.html)

### Platform

| carbon | cocoa | win32 | win64 |
|:------:|:-----:|:---------:|:---------:|
|<img src="https://cloud.githubusercontent.com/assets/1725068/22371562/1b091f0a-e4db-11e6-8458-8653954a7cce.png" width="24" height="24" />|<img src="https://cloud.githubusercontent.com/assets/1725068/22371562/1b091f0a-e4db-11e6-8458-8653954a7cce.png" width="24" height="24" />|<img src="https://cloud.githubusercontent.com/assets/1725068/22371562/1b091f0a-e4db-11e6-8458-8653954a7cce.png" width="24" height="24" />|<img src="https://cloud.githubusercontent.com/assets/1725068/22371562/1b091f0a-e4db-11e6-8458-8653954a7cce.png" width="24" height="24" />|

### Version

<img src="https://cloud.githubusercontent.com/assets/1725068/18940649/21945000-8645-11e6-86ed-4a0f800e5a73.png" width="32" height="32" /> <img src="https://cloud.githubusercontent.com/assets/1725068/18940648/2192ddba-8645-11e6-864d-6d5692d55717.png" width="32" height="32" /> <img src="https://user-images.githubusercontent.com/1725068/41266195-ddf767b2-6e30-11e8-9d6b-2adf6a9f57a5.png" width="32" height="32" />

![preemption xx](https://user-images.githubusercontent.com/1725068/41327179-4e839948-6efd-11e8-982b-a670d511e04f.png)

## Syntax


```
zones:=TZ Get zones
```

Parameter|Type|Description
------------|------------|----
zones|TEXT|``json``

```
result:=TZ Convert (time;fmt_in;zone_out;fmt_out)
```

Parameter|Type|Description
------------|------------|----
time|TEXT|
fmt_in|TEXT|``strftime``
zone_out|TEXT|
fmt_out|TEXT|``strftime``
offset|LONGINT|seconds

### Examples

```
  //RFC to ISO conversion (specify format only)

$time:="Sun Sep 16 01:03:52 -0500 1973"
$fmt_in:="%a %b %d %T %z %Y"
$zone_out:=""
$fmt_out:="%FT%TZ"

$utc:=TZ Convert ($time;$fmt_in;$zone_out;$fmt_out)
  //1973-09-16T06:03:52.000Z

  //RFC to ISO conversion in zone (specify format and zone)

$time:="Sun Sep 16 01:03:52 -0500 1973"
$fmt_in:="%a %b %d %T %z %Y"
$zone_out:="Australia/Sydney"
$fmt_out:="%FT%T %Z"

$aest:=TZ Convert ($time;$fmt_in;$zone_out;$fmt_out)
  //1973-09-16 16:03:52.000 AEST
```

```
  //duration over time zone change 

$departure:="1978-12-30 12:01:00 -0500"
$fmt_in:="%F %T %z"
$fmt_out:="%F %T %z"
$zone_out:="Asia/Tehran"
$flight:=?14:44:00?

$arrival:=TZ Convert ($departure;\
$fmt_in;\
$zone_out;\
$fmt_out;\
$flight+0)
  //1978-12-31 11:45:00.000 +0400

  //day later...
$departure:=TZ Convert ($departure;\
$fmt_in;\
"America/New_York";\
$fmt_out;\
?24:00:00?+0)
  //1978-12-31 12:01:00.000 -0500

$arrival:=TZ Convert ($departure;\
$fmt_in;\
$zone_out;\
$fmt_out;\
$flight+0)
  //1979-01-01 11:15:00.000 +0330
```
