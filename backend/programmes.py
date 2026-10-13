"""Public distributor, festival and photography-call metadata; no booking actions."""
import json
import re
from datetime import date, datetime
from urllib.parse import urljoin, urlsplit, parse_qsl, urlencode, urlunsplit
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from .ingestion import content_record, event_record, stable_id, canonical_url

MONTHS_EN = {month: number for number, month in enumerate(('January','February','March','April','May','June','July','August','September','October','November','December'),1)}
MONTHS_FR = {month: number for number, month in enumerate(('janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'),1)}


def diaphana_records(source, payload):
    soup=BeautifulSoup(payload,'html.parser');records,events,links,seen=[],[],[],set()
    for card in soup.select('.slide-content'):
        title,dates,anchor=card.select_one('.slide-title'),card.select_one('.slide-date'),card.select_one('a[href*="/film/"]')
        if not title or not dates or not anchor:continue
        original=dates.get_text(' ',strip=True);match=re.fullmatch(r'(\d{1,2}) (\w+) (\d{4})',original)
        if not match or match[2].lower() not in MONTHS_FR:continue
        day=date(int(match[3]),MONTHS_FR[match[2].lower()],int(match[1])).isoformat()
        url=canonical_url(urljoin(source['feed_url'],anchor['href']))
        if url in seen:continue
        seen.add(url);name=title.get_text(' ',strip=True)
        record=content_record(source,name,url,summary=f'法国发行商 Diaphana 公布《{name}》的法国院线上映日期为 {day}；出行前请核对原文及影院排片。')
        event=event_record(source,record,'cinema_release',day,country='FR',timezone='Europe/Paris')
        event['date_text_original']=original
        records.append(record);events.append(event);links.append({'content_id':record['id'],'event_id':event['id']})
    if not records:raise ValueError('没有明确年份的法国上映安排')
    return records,events,links


def js_array(text,name):
    marker=re.search(r'\b'+re.escape(name)+r'\s*:\s*',text)
    if not marker:raise ValueError('节目数据结构缺失')
    # Parse the public string/array data only. Never evaluate site JavaScript.
    values,_=json.JSONDecoder().raw_decode(text[marker.end():].replace("\\'","'"))
    if not isinstance(values,list):raise ValueError('节目数据不是数组')
    return values


FILM_STRANDS={'LFFGALA','LFFGALAREPEAT','LFFAWARDS','LFFSPECIAL','LFFLOVE','LFFJOURNEY','LFFDARE','LFFLAUGH','LFFTHRILL','LFFCULT','LFFCREATE','LFFTREASURES','LFFSHORTS','LFFDEBATE','LFFFAMILY'}


def bfi_records(source,payload):
    text=payload.decode('utf-8');soup=BeautifulSoup(text,'html.parser')
    if not soup.title or 'BFI London Film Festival' not in soup.title.get_text():raise ValueError('并非已核实的伦敦影展节目页')
    columns=js_array(text,'searchNames');rows=js_array(text,'searchResults')
    records,events,links={},{},[]
    for values in rows:
        row=dict(zip(columns,values))
        if row.get('object_type')!='P' or row.get('data3') not in FILM_STRANDS:continue
        name=row.get('description');original=row.get('start_date','');venue=row.get('venue_description')
        match=re.search(r'(\d{1,2}) (\w+) (\d{4}) (\d{2}):(\d{2})$',original)
        if not name or not venue or not match or match[2] not in MONTHS_EN or not row.get('id'):continue
        instant=datetime(int(match[3]),MONTHS_EN[match[2]],int(match[1]),int(match[4]),int(match[5]),tzinfo=ZoneInfo('Europe/London'))
        booking=canonical_url(urljoin(source['feed_url'],row['additional_info']))
        parts=urlsplit(booking)
        query=[(k,v) for k,v in parse_qsl(parts.query) if not k.endswith('::context_id')]
        url=urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(query),'')).strip()
        record=content_record(source,name,url,summary=f'BFI 伦敦电影节官方放映信息《{name}》。具体场次、当地时刻、场馆与票价见关联活动；售罄或节目变更请核对原文。')
        record['original_page_url']=booking
        event=event_record(source,record,'festival_screening',instant.date().isoformat(),venue=venue,city='伦敦',country='GB',timezone='Europe/London')
        event.update(id=stable_id(source['id']+':performance:'+row['id']),start_at=instant.isoformat(),time_status='confirmed',date_text_original=original,booking_url=booking)
        low,high=row.get('min_price'),row.get('max_price')
        if low and high:event['price_text']=f'官网显示 {low}–{high}；优惠资格与预约手续费另查原文。'
        event['booking_status']='sold_out' if row.get('availability_status')=='S' else 'check_original'
        records[record['id']]=record;events[event['id']]=event;links.append({'content_id':record['id'],'event_id':event['id']})
    if not records:raise ValueError('未解析到有明确时刻的电影放映')
    return list(records.values()),list(events.values()),links


def wpo_records(source,payload):
    soup=BeautifulSoup(payload,'html.parser');main=soup.select_one('#block-wpo-content article')
    if not main or not main.find('h1'):raise ValueError('征集主体资料缺失')
    text=main.get_text(' ',strip=True);heading=main.find('h1').get_text(' ',strip=True)
    month='|'.join(MONTHS_EN)
    # Require a deadline sentence, never a judging date or publication period.
    after=re.compile(r'(?:Deadline(?: for entries)? (?:is )?|Entries must be submitted (?:by|between).{0,45}?)(\d{1,2})\s+('+month+r'),?\s+(\d{4})\s*(?:at|-)\s*(\d{1,2})[.:](\d{2})\s*\(?GMT\)?',re.I)
    before=re.compile(r'Entries must be submitted by\s*(\d{1,2})[.:](\d{2})\s*GMT on\s*(\d{1,2}) ('+month+r') (\d{4})',re.I)
    deadlines=[]
    for m in after.finditer(text):deadlines.append((int(m[3]),MONTHS_EN[m[2].title()],int(m[1]),int(m[4]),int(m[5])))
    for m in before.finditer(text):deadlines.append((int(m[5]),MONTHS_EN[m[4].title()],int(m[3]),int(m[1]),int(m[2])))
    if not deadlines:raise ValueError('缺少可核实的截止日期与 GMT 时区')
    dates={d[:3] for d in deadlines}
    if len(dates)!=1:raise ValueError('官方截止日期存在冲突')
    y,mo,day=next(iter(dates));stamp=date(y,mo,day).isoformat()
    # Additional upload requirements on the same date may contradict the header.
    upload=re.compile(r'uploaded by\s*(\d{1,2})[.:](\d{2})\s*GMT on\s*'+str(day)+r' '+list(MONTHS_EN)[mo-1]+r' '+str(y),re.I)
    times={d[3:] for d in deadlines}|{(int(m[1]),int(m[2])) for m in upload.finditer(text)}
    url=source['feed_url'];name=f"Sony World Photography Awards {source['entry_label_zh']}"
    record=content_record(source,heading,url,summary=f'{name}：官方截止日期为 {stamp}，使用 GMT。报名资格、费用与版权条款请查看官网完整规则。')
    record['title_zh']=name
    event=event_record(source,record,'call_deadline',stamp,country='GLOBAL',timezone='UTC')
    event['title_zh']=name;event['date_text_original']=f'{stamp} GMT'
    if len(times)==1:
        hour,minute=next(iter(times));event['deadline_at']=datetime(y,mo,day,hour,minute,tzinfo=ZoneInfo('UTC')).isoformat();event['time_status']='confirmed'
    else:
        event['time_status']='conflict';event['time_note']='官方时刻存在冲突：'+ ' / '.join(f'{h:02}:{m:02} GMT' for h,m in sorted(times))+'；简介与上传规则表述不同，请向主办方核对，勿依赖单一时刻。'
    entries={canonical_url(urljoin(url,a['href'])) for a in soup.select('a[href]') if a.get_text(' ',strip=True).lower()=='enter competition' and urlsplit(urljoin(url,a['href'])).hostname==source.get('entry_host','users.worldphoto.org')}
    entry_url=next(iter(entries)) if len(entries)==1 else None
    if entry_url:
        event['booking_url']=entry_url
        competition=re.search(r'/competition/(\d+)',event['booking_url'])
        if competition:event['id']=stable_id(source['id']+':competition:'+competition[1])
    if 'Enter up to three single images for free' in text:event['price_text']='最多 3 张免费；增加作品可购买额外名额，金额与条件见官网。'
    elif re.search(r'free to enter',text,re.I):event['price_text']='官网说明参赛免费；资格、提交限制与版权条款见规则。'
    event['eligibility_note']=source.get('eligibility_note')
    return [record],[event],[{'content_id':record['id'],'event_id':event['id']}]


def mmca_records(source,payload):
    soup=BeautifulSoup(payload,'html.parser');records,events,links,seen=[],[],[],set()
    for anchor in soup.select('a[onclick*="fn_Detail"]'):
        title,dates,venue=anchor.select_one('p.tit'),anchor.select_one('span.txt'),anchor.select_one('span.ctg')
        match=re.search(r"fn_Detail\('([0-9]+)'\)",anchor.get('onclick',''))
        if not title or not dates or not venue or not match or venue.get_text(strip=True)!='Seoul':continue
        days=re.fullmatch(r'(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})',dates.get_text(strip=True))
        if not days or match[1] in seen:continue
        seen.add(match[1]);url=source['detail_url_template'].format(id=match[1]);name=title.get_text(' ',strip=True)
        record=content_record(source,name,url,summary=f'韩国国立现代美术馆首尔馆展览《{name}》，官网展期 {days[1]} 至 {days[2]}；票价、开放日与预约请核对原文。')
        from .reading import image_fields
        image=anchor.find('img')
        if image:record.update(image_fields(source,image.get('data-src') or image.get('src'),url,name))
        event=event_record(source,record,'exhibition',days[1],days[2],'MMCA Seoul','首尔','KR','Asia/Seoul')
        event['date_text_original']=dates.get_text(strip=True)
        records.append(record);events.append(event);links.append({'content_id':record['id'],'event_id':event['id']})
    if not records:raise ValueError('没有可核实的首尔馆完整展期')
    return records,events,links
