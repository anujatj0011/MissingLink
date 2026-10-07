from pathlib import Path
import json
import gzip
import os
from urllib.request import Request, urlopen
from urllib.error import URLError
import numpy as np
import pandas as pd
import streamlit as st
from engine import match, clock

st.set_page_config(page_title='MissingLink · Better transfers',page_icon='🔗',layout='wide',initial_sidebar_state='collapsed')
st.markdown('''<style>
.stApp{background:linear-gradient(180deg,#f7fbfb 0%,#ffffff 36%)} .block-container{max-width:1240px;padding-top:1.5rem;padding-bottom:3rem}
h1,h2,h3{color:#16324a;letter-spacing:-.025em}
[data-testid="stMetric"]{background:#fff;padding:17px 18px;border-radius:16px;border:1px solid #e2eaed;box-shadow:0 5px 18px rgba(22,50,74,.045)}
[data-testid="stMetricLabel"]{color:#6b7b87} [data-testid="stExpander"]{background:#fff;border-radius:14px}
[data-testid="stDataFrame"]{border:1px solid #e2eaed;border-radius:14px;overflow:hidden} div.stButton>button{border-radius:11px}
.hero{padding:1.8rem 2rem;border:1px solid #dfe9eb;border-radius:22px;background:linear-gradient(125deg,#eaf6f5 0%,#fff 62%,#f5f9fb 100%);box-shadow:0 10px 30px rgba(22,50,74,.055);margin-bottom:1rem}
.eyebrow{font-size:.74rem;letter-spacing:.12em;text-transform:uppercase;color:#168b87;font-weight:800}
.hero h1{font-size:3rem;line-height:1;margin:.35rem 0 .65rem}.hero p{font-size:1.08rem;color:#61717d;max-width:850px;line-height:1.6;margin:0}
.case{padding:1.2rem 1.35rem;border-radius:16px;background:#f0f8f7;border:1px solid #d9ebe9;margin:.6rem 0 1rem}.case strong{color:#16324a}
@media(max-width:900px){.hero{padding:1.3rem}.hero h1{font-size:2.2rem}.block-container{padding-left:1rem;padding-right:1rem}}
</style>''',unsafe_allow_html=True)
st.markdown('''<div class="hero"><div class="eyebrow">Dublin public transport · decision-support prototype</div>
<h1>Missing<span style="color:#168b87">Link</span></h1>
<p>Find where scheduled transfers repeatedly fail, see which places deserve attention, and test small timetable shifts before deeper operational analysis.</p></div>''',unsafe_allow_html=True)
st.caption('NTA scheduled services · Representative weekday · Morning 07:00–10:00 & evening 16:00–19:00 · 2-minute boarding allowance')
DATA = Path(__file__).parent/'data'

@st.cache_data(show_spinner=False)
def results(signature):
    poor = pd.read_csv(DATA/'poor-transfers.csv',dtype={'stop_id':str,'source':str,'target':str,'id':str},keep_default_na=False)
    scenarios = pd.read_csv(DATA/'improvement-scenarios.csv')
    summary = json.loads((DATA/'analysis-summary.json').read_text())
    return poor,scenarios,summary

@st.cache_data(show_spinner=False)
def transfer_index(signature):
    with gzip.open(DATA/'transfer-index.json.gz','rt',encoding='utf-8') as file:
        return json.load(file)

try:
    poor,scenarios,summary = results((DATA/'analysis-summary.json').stat().st_mtime)
except (FileNotFoundError,ValueError):
    st.error('The bundled analysis is unavailable. Restore the app’s data folder or run build_analysis.py.')
    st.stop()
if poor.empty:
    st.info('No connection meets the repeated near-miss rule in the included timetable.')
    st.stop()


def opportunity_table(frame):
    return frame[['connection','period','median','best_shift','best_median']].rename(columns={
        'connection':'Connection','period':'Peak','median':'Current wait · min',
        'best_shift':'Shift · +min','best_median':'Simulated wait · min'}).round(1)

c1,c2,c3 = st.columns(3)
c1.metric('📍 Locations flagged',f'{poor.stop_id.nunique():,}')
c2.metric('🔗 Poor transfer patterns',f'{len(poor):,}')
c3.metric('↗ Improvement potential',f'{summary["improvement_locations"]:,} places')

f1,f2 = st.columns([3,1])
query = f1.text_input('Find a place or route',placeholder='Search all results…')
period = f2.selectbox('Peak period',['Both peaks','Morning','Evening'])
filtered = poor.copy()
if query:
    filtered = filtered[filtered.location.str.contains(query,case=False,regex=False) | filtered.connection.str.contains(query,case=False,regex=False)]
if period != 'Both peaks':
    filtered = filtered[filtered.period==period]
if filtered.empty:
    st.info('No findings match these filters.')
    st.stop()
leaders = filtered.sort_values(['saving','score'],ascending=False).drop_duplicates('stop_id')
counts = filtered.groupby('stop_id').size()
leaders = leaders.copy()
leaders['patterns'] = leaders.stop_id.map(counts)
top = leaders.head(5)
overview,all_results = st.tabs(['Overview','All locations & results'])
with overview:
    left,right = st.columns([1.1,1])
    with left:
        st.subheader('Where to investigate')
        st.map(leaders[['lat','lon']],zoom=10,height=350)
    with right:
        st.subheader('Five priority places')
        for i,r in enumerate(top.itertuples(),1):
            with st.container(border=True):
                st.markdown(f'**{i}. {r.location}**')
                st.caption(f'{r.patterns} poor connections · {r.period} · {r.connection}')
                st.markdown(f'**{r.median:.1f} → {r.best_median:.1f} min** · investigate a **+{int(r.best_shift)} min** shift')
    st.caption('Ranked by the strongest connection’s simulated median wait reduction at each stop. Benefits are not added across locations.')
    with st.expander('Findings summary',expanded=True):
        for r in top.itertuples():
            st.markdown(f'• **{r.location}:** {r.connection} has a {r.median:.1f}-minute median wait. A +{int(r.best_shift)}-minute shift gives {r.best_median:.1f} minutes in simulation; {int(r.improved)} arrivals improve and {int(r.worsened)} worsen, from {int(r.arrivals)} scheduled arrivals.')
        st.caption('Calculated summary. Validate passenger demand, punctuality, driver and fleet constraints, and effects elsewhere before changing a timetable.')
    if st.button('Explain the findings',type='primary'):
        api_key = os.environ.get('OPENAI_API_KEY','')
        if not api_key:
            st.info('AI explanation is not connected yet. Configure OPENAI_API_KEY on the server. The calculated findings above are available now.')
        else:
            payload = {'model':os.environ.get('OPENAI_MODEL','gpt-5'), 'store':False,
                'instructions':'Explain transfer-analysis evidence in five short bullets, one per place. Use only supplied numbers. Explain poor waits, the proposed shift, sample size and worsened arrivals. Never invent savings, changes or operational feasibility. End with one sentence on validation. These are same-stop scheduled arrivals, not passengers; each shift is an independent scenario.',
                'input':top[['location','connection','period','patterns','arrivals','near_rate','median','best_shift','best_median','improved','worsened']].to_json(orient='records')}
            try:
                with st.spinner('Explaining calculated findings…'):
                    request = Request('https://api.openai.com/v1/responses',data=json.dumps(payload).encode(),
                        headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'})
                    with urlopen(request,timeout=45) as response:
                        result = json.load(response)
                    explanation = '\n'.join(c['text'] for item in result.get('output',[]) for c in item.get('content',[]) if c.get('type')=='output_text')
                    if not explanation:
                        raise ValueError('No explanation returned')
                    st.session_state['explanation'] = (filtered.id.tolist(),explanation)
            except (URLError,ValueError,TimeoutError):
                st.warning('The AI service could not return an explanation. The calculated findings remain available.')
    cached = st.session_state.get('explanation')
    if cached and cached[0] == filtered.id.tolist():
        st.markdown(cached[1])
        st.caption('AI explanation of calculated findings; verify against the evidence below.')
with all_results:
    st.subheader(f'All {len(leaders):,} locations · {len(filtered):,} poor connections')
    grouped = leaders[['location','patterns','median','best_shift','best_median','saving']].rename(columns={
        'location':'Place','patterns':'Poor connections','median':'Current wait · min','best_shift':'Shift · +min',
        'best_median':'Simulated wait · min','saving':'Largest reduction · min'})
    st.dataframe(grouped.round(1),hide_index=True,width='stretch',height=400)
    st.caption('Each row shows the strongest opportunity at one stop. Explore a place below to see every connection together.')
    st.download_button('Download all filtered findings',filtered.to_csv(index=False),'missinglink-opportunities.csv','text/csv')
    st.download_button('Download full analysis · all connections',(DATA/'all-connections.csv.gz').read_bytes(),'missinglink-all-connections.csv.gz','application/gzip')

st.divider()
st.markdown('## Explore a place')
st.caption('Move from network-level screening to the evidence behind one stop and connection.')
labels = leaders.set_index('stop_id')
stop_id = st.selectbox('Location',leaders.stop_id.tolist(),format_func=lambda key:f'{labels.loc[key,"location"]} · {int(labels.loc[key,"patterns"])} poor connections · {key}')
place = filtered[filtered.stop_id==stop_id]
st.dataframe(opportunity_table(place),hide_index=True,width='stretch')
st.caption('Suggested shifts are alternatives for individual connections; they are not a combined timetable plan.')
with st.expander('Try a timetable change · optional'):
    choices = place.set_index('id')
    selected_id = st.selectbox('Connection',place.id.tolist(),format_func=lambda key:f'{choices.loc[key,"connection"]} · {choices.loc[key,"period"]}')
    row = choices.loc[selected_id]
    shift = st.slider('Delay connecting departures · minutes',0,10,int(row.best_shift),key='shift-'+selected_id)
    scenario = scenarios[(scenarios.id==selected_id)&(scenarios['shift']==shift)].iloc[0]
    before,after = st.columns(2)
    before.metric('Current median wait',f'{row["median"]:.1f} min')
    after.metric('Simulated median wait',f'{scenario["median"]:.1f} min')
    st.caption(f'{int(scenario.improved)} arrivals improve · {int(scenario.worsened)} worsen · {int(row.arrivals)} arrivals analysed')
    lookup = transfer_index((DATA/'transfer-index.json.gz').stat().st_mtime)[stop_id]
    start,end = (7*3600,10*3600) if row.period=='Morning' else (16*3600,19*3600)
    b = np.asarray(lookup[row.target]['departures'])
    all_before,all_after = [],[]
    for group,times in lookup.items():
        if group.rsplit(' | ',1)[0] == row.target.rsplit(' | ',1)[0]:
            continue
        a = np.asarray(times['arrivals'])
        a = a[(a>=start)&(a<end)]
        if len(a):
            all_before.extend(match(a,b,2)['wait'].tolist())
            all_after.extend(match(a,b,2,shift)['wait'].tolist())
    old,new = np.asarray(all_before),np.asarray(all_after)
    improved = ((np.isfinite(old)&np.isfinite(new)&(new<old)) | (~np.isfinite(old)&np.isfinite(new))).sum()
    worsened = ((np.isfinite(old)&np.isfinite(new)&(new>old)) | (np.isfinite(old)&~np.isfinite(new))).sum()
    st.markdown(f'**Stop-wide check:** {int(improved)} arrival opportunities improve and {int(worsened)} worsen across all other incoming routes in this peak ({len(old)} opportunities).')
    st.caption('This check includes other incoming routes at this stop. Repeated arrivals across routes are not passenger counts. Effects at other stops are not modelled.')
    with st.expander('Show evidence'):
        a = np.asarray(lookup[row.source]['arrivals'])
        a = a[(a>=start)&(a<end)]
        baseline,changed = match(a,b,2),match(a,b,2,shift)
        evidence = pd.DataFrame({'Incoming arrival':baseline.arrival.map(clock),'Current departure':baseline['next'].map(clock),
            'Shifted departure':changed['next'].map(clock),'Current wait · min':baseline.wait,'Simulated wait · min':changed.wait})
        st.dataframe(evidence.round(1),hide_index=True,width='stretch')
        st.caption(f'Incoming destination: {row.incoming_destinations} · Connecting destination: {row.outgoing_destinations}')
with st.expander('Method & scope'):
    st.write('Real NTA weekday GTFS, same-stop transfers in Dublin. Morning 07:00–10:00 and evening 16:00–19:00, with a two-minute boarding allowance. A poor pattern has at least three arrivals and at least 40% near-misses: ready 1–5 minutes after departure, then waiting at least 15 minutes. Median waits exclude arrivals with no later service. Suggestions test 0–10 minute shifts, prioritising unmatched arrivals, then median wait, then worsened arrivals and smaller shifts. Rankings are not passenger weighted. Nearby stops, live reliability and network-wide feasibility are outside scope.')
st.caption('Source: National Transport Authority · Irish Public Sector Data · CC BY 4.0 · Scheduled-service analysis')

