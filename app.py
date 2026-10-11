from flask import Flask, render_template, request, redirect, url_for, flash, Response
from jinja2 import DictLoader
import sqlite3, json, os
from datetime import date, timedelta
from pathlib import Path
from contextlib import contextmanager

ROOT = Path(__file__).parent
app = Flask(__name__)
app.jinja_loader = DictLoader({
    'confirm.html': (
        '{% extends \'base.html\' %}{% block content %}<section class="new-trip"><d'
        'iv><h2>Remove {{ kind }}?</h2><p>This removes the {{ kind }} and its ass'
        'ociated data. This cannot be undone.</p></div><form method="post" action'
        '="{{ action }}"><button>Confirm removal</button> <a class="button second'
        'ary" href="{{ url_for(\'trip\',t=t) }}">Cancel</a></form></section>{% endb'
        'lock %}'
    ),
    'home.html': (
        '{% extends \'base.html\' %}{% block content %}<section class="hero"><div><'
        'span class="eyebrow">YOUR NEXT GETAWAY STARTS HERE</span><h1>From groupc'
        'hat<br>to <em>getaway.</em></h1><p>Find the place, the dates, and the bu'
        'dget that bring everyone along. Your next adventure starts here.</p><a c'
        'lass="button" href="#new-trip">Plan something good</a><div class="hero-c'
        'aption">ONE SHARED PLAN. ENDLESS POSSIBILITIES.</div></div><div class="s'
        'ky-art" aria-hidden="true"><div class="orbit"></div><div class="sun"></d'
        'iv><div class="cloud c1"></div><div class="cloud c2"></div><div class="p'
        'lane">✈</div><div class="ticket"><span>YOUR NEXT ADVENTURE</span><strong'
        '>Anywhere, together.</strong><div>BOARDING PASS <b>↗</b></div></div><spa'
        'n class="art-caption">GOOD COMPANY. GREAT DISTANCES.</span></div></secti'
        'on><section class="section-heading"><div><span class="eyebrow">YOUR DEPA'
        'RTURE BOARD</span><h2>Adventures in the making</h2></div><span class="pi'
        'll">{{ trips|length }} trips planned</span></section><div class="trip-gr'
        'id">{% for trip in trips %}<article class="trip-card"><a class="trip-car'
        'd-link" href="{{ url_for(\'trip\',t=trip.id) }}"><div class="card-art art-'
        '{{ loop.index % 3 }}"><span>✈</span><small>{{ trip.departure or \'Departu'
        're undecided\' }}</small></div><div class="card-body"><span class="eyebro'
        'w">Start Packing!</span><h3>{{ trip.name }}</h3>{% if trip.destination_c'
        'ity or trip.description %}<p>{{ trip.destination_city or trip.descriptio'
        'n }}</p>{% endif %}</div></a><div class="trip-delete"><a class="danger" '
        'href="{{ url_for(\'confirm_remove\',t=trip.id,kind=\'trip\',item=trip.id) }}'
        '">Delete trip</a></div></article>{% else %}<div class="empty">No trips y'
        'et. Create your first trip below.</div>{% endfor %}</div><section id="ne'
        'w-trip" class="new-trip"><div><span class="eyebrow">START WITH AN IDEA</'
        'span><h2>Where are we going?</h2><p>You don’t need all the answers yet.<'
        '/p></div><form action="/create" method="post"><label>Trip name<input nam'
        'e="name" placeholder="Winter 2026" required maxlength="120"></label><div'
        ' class="departure-row"><label>Departure city<input name="departure" plac'
        'eholder="New York" maxlength="120"></label></div><button>Create trip</bu'
        'tton></form></section>{% endblock %}\n'
    ),
    'base.html': (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="v'
        'iewport" content="width=device-width, initial-scale=1"><title>CarryOn · '
        'From groupchat to getaway.</title><link rel="stylesheet" href="{{ url_fo'
        'r(\'stylesheet\') }}"></head><body><header><a class="brand" href="/"><span'
        '>CarryOn<span class="brand-dot">.</span></span></a></header><main>{% for'
        ' message in get_flashed_messages() %}<div role="status" class="notice">{'
        '{ message }}</div>{% endfor %}{% block content %}{% endblock %}</main></'
        'body></html>\n'
    ),
    'person_fields.html': (
        '<div class="form-row"><label>Name<input name="name" value="{{ person.nam'
        'e if person else \'\' }}" required maxlength="120"></label><label>Maximum '
        'budget ($)<input name="budget" type="number" min="0" max="10000000" step'
        '="0.01" value="{{ person.budget if person else \'\' }}" required></label><'
        'label>Preferred trip length (days)<input name="length" type="number" min'
        '="1" max="90" value="{{ person.length if person else 5 }}" required></la'
        'bel></div><label>Available date ranges · one per line<textarea name="ran'
        'ges" rows="3" placeholder="2026-12-12 to 2026-12-31" required>{{ person.'
        "ranges_text if person else '' }}</textarea></label>\n"
    ),
    'trip.html': (
        "{% extends 'base.html' %}{% block content %}{% if request.args.get('summ"
        'ary\') %}<div class="notice no-print">Use your browser’s Print command to'
        ' print this summary or save it as PDF.</div>{% endif %}<div class="trip-'
        'title"><div><a class="breadcrumb" href="/">All trips</a><span class="eye'
        'brow">DEPARTING FROM {{ trip.departure or \'ANYWHERE\' }}</span><h1>{{ tri'
        'p.name }}</h1><p>{{ trip.destination_city or trip.description }}</p></di'
        'v><a class="button secondary no-print" href="{{ url_for(\'trip\',t=trip.id'
        ',summary=1) }}">Printable summary</a></div><nav class="tabs no-print"><a'
        ' href="#crew">01 · Your crew</a><a href="#destinations">02 · Destination'
        's</a><a href="#dates">03 · Find dates</a><a href="#itinerary">04 · Itine'
        'rary</a></nav><div class="stats"><div><strong>{{ people|length }}</stron'
        'g><span>travel companions</span></div><div><strong>{{ destinations|lengt'
        "h }}</strong><span>places to explore</span></div><div><strong>{{ '$%0.0f"
        "'|format((people|map(attribute='budget')|min)) if people else '—' }}</st"
        'rong><span>budget that fits everyone</span></div><div><strong>{{ windows'
        "[0].count ~ '/' ~ people|length if windows else '—' }}</strong><span>bes"
        't date overlap</span></div></div>\n<section id="crew"><div class="section'
        '-heading"><div><span class="eyebrow">THE BEST PART IS WHO’S COMING</span'
        '><h2>Your travel crew</h2></div></div><p class="muted">Preferred trip le'
        'ngth is the longest trip each person wants to take. Dates include both a'
        'rrival and departure days.</p><div class="crew-grid">{% for p in people '
        '%}<article class="person"><div class="person-head"><span class="avatar">'
        "{{ p.name[:1]|upper }}</span><div><h3>{{ p.name }}</h3><span>${{ '%0.0f'"
        '|format(p.budget) }} · up to {{ p.length }} days</span></div></div><p cl'
        'ass="date-text">{{ p.ranges_text }}</p><details class="no-print"><summar'
        'y>Edit details</summary><form method="post" action="{{ url_for(\'person\','
        't=trip.id) }}"><input type="hidden" name="id" value="{{ p.id }}">{% set '
        "person=p %}{% include 'person_fields.html' %}<button>Save changes</butto"
        'n></form><a class="danger" href="{{ url_for(\'confirm_remove\',t=trip.id,k'
        'ind=\'person\',item=p.id) }}">Remove participant</a></details></article>{%'
        ' else %}<div class="empty">Add your friends to compare budgets and dates'
        '.</div>{% endfor %}</div><details class="no-print"><summary>＋ Add a trav'
        'el companion</summary><form method="post" action="{{ url_for(\'person\',t='
        'trip.id) }}">{% set person=none %}{% include \'person_fields.html\' %}<but'
        'ton>Add companion</button></form></details></section>\n<section id="desti'
        'nations"><div class="section-heading"><div><span class="eyebrow">PICK YO'
        'UR KIND OF ADVENTURE</span><h2>Somewhere worth going</h2></div><span cla'
        'ss="pill">Costs are estimates · USD / person</span></div><p class="muted'
        '">Ranked by 2 points per vote + 1 point per person whose budget covers t'
        'he estimate. Vote for as many places as you like.</p><div class="destina'
        'tion-grid">{% for d in destinations %}<article class="destination"><div '
        'class="destination-art art-{{ loop.index % 3 }}"><span class="rank">0{{ '
        'loop.index }}</span><span class="landscape">{{ [\'☀\',\'⛰\',\'≈\'][loop.index '
        '% 3] }}</span><span class="location-label">{{ d.name }}</span></div><div'
        ' class="card-body"><div class="destination-title"><h3>{{ d.name }}</h3><'
        "strong>${{ '%0.0f'|format(d.cost) }}</strong></div><p>{{ d.description }"
        '}</p><div class="metrics"><span>♥ {{ d.votes }} votes</span><span>{{ d.a'
        'ffordable }}/{{ people|length }} within budget</span></div><p class="sco'
        're">{{ d.score }} points · {{ d.votes }} × 2 + {{ d.affordable }} budget'
        ' matches</p><div class="vote-list no-print">{% for p in people %}<form m'
        'ethod="post" action="{{ url_for(\'vote\',t=trip.id) }}"><input type="hidde'
        'n" name="person" value="{{ p.id }}"><input type="hidden" name="destinati'
        'on" value="{{ d.id }}"><button class="vote {{ \'selected\' if (p.id,d.id) '
        'in votes }}" aria-pressed="{{ \'true\' if (p.id,d.id) in votes else \'false'
        '\' }}">{{ p.name }} {{ \'♥\' if (p.id,d.id) in votes else \'+\' }}</button></'
        'form>{% endfor %}</div><div class="no-print destination-remove"><a class'
        '="danger" href="{{ url_for(\'confirm_remove\',t=trip.id,kind=\'destination\''
        ',item=d.id) }}">Remove destination</a></div></div></article>{% else %}<d'
        'iv class="empty">Your world is wide open. Add your first destination bel'
        'ow.</div>{% endfor %}</div>{% if people and destinations and not destina'
        "tions|selectattr('affordable','equalto',people|length)|list %}<div class"
        '="notice">No destination fits everyone’s budget yet. Try a lower-cost de'
        'stination, shorten the trip, or revise the estimates together.</div>{% e'
        'ndif %}<details class="no-print"><summary>＋ Suggest a destination</summa'
        'ry><form method="post" action="{{ url_for(\'destination\',t=trip.id) }}" c'
        'lass="form-row"><label>Destination<input name="name" required placeholde'
        'r="London" maxlength="120"></label><label>Description<input name="descri'
        'ption" placeholder="What makes it special?" maxlength="500"></label><lab'
        'el>Estimated cost per person ($)<input type="number" name="cost" min="0"'
        ' max="10000000" step="0.01" required></label><button>Add destination</bu'
        'tton></form></details></section>\n<section id="dates"><div class="section'
        '-heading"><div><span class="eyebrow">MAKE YOUR CALENDARS AGREE</span><h2'
        '>A window to get away</h2></div></div>{% if windows %}{% if windows[0].c'
        'ount < people|length %}<div class="notice">There isn’t a window for ever'
        'yone at their preferred lengths. These options include the most people. '
        'Try shorter preferred lengths or add more availability to find another o'
        'verlap.</div>{% endif %}<div class="windows">{% for w in windows %}<div '
        'class="window"><span class="window-icon">↗</span><div><strong>{{ w.start'
        " }} → {{ w.end }}</strong><p>{{ w.length }} days · {{ w.names|join(', ')"
        ' }}</p></div><span class="pill {{ \'green\' if w.count==people|length }}">'
        '{{ w.count }}/{{ people|length }} available</span><a class="button secon'
        'dary no-print" href="{{ url_for(\'trip\',t=trip.id,start=w.start,end=w.end'
        ') }}#itinerary">Use dates</a></div>{% endfor %}</div>{% else %}<div clas'
        's="empty">Add a friend\'s availability to find travel windows.</div>{% en'
        'dif %}</section>\n<section id="itinerary" class="itinerary"><div class="s'
        'ection-heading"><div><span class="eyebrow">TURN THE MAYBE INTO A PLAN</s'
        'pan><h2>Your boarding pass</h2></div><span class="pill">{{ \'Plan confirm'
        "ed' if trip.chosen else 'Still dreaming' }}</span></div>{% if trip.chose"
        'n %}<div class="confirmed"><h3>{% for d in destinations %}{% if d.id==tr'
        'ip.chosen %}{{ d.name }}{% endif %}{% endfor %}</h3><p>{{ trip.start }} '
        "→ {{ trip.end }}</p><p><b>Accommodation:</b> {{ trip.accommodation or 'T"
        'o be decided\' }}</p><p class="preserve">{{ trip.notes }}</p></div>{% end'
        'if %}<form method="post" action="{{ url_for(\'confirm\',t=trip.id) }}" cla'
        'ss="no-print"><div class="form-row"><label>Destination<select name="dest'
        'ination" required><option value="">Choose your destination</option>{% fo'
        'r d in destinations %}<option value="{{ d.id }}" {{ \'selected\' if trip.c'
        'hosen==d.id }}>{{ d.name }}</option>{% endfor %}</select></label><label>'
        'Arrival<input type="date" id="plan-start" name="start" value="{{ selecte'
        'd_start }}" required></label><label>Departure<input type="date" id="plan'
        '-end" name="end" value="{{ selected_end }}" required></label></div><labe'
        'l>Accommodation<input name="accommodation" value="{{ trip.accommodation '
        '}}" placeholder="Stay details or options to explore" maxlength="500"></l'
        'abel><label>Trip notes<textarea name="notes" rows="3" placeholder="Thing'
        's to pack, places to eat, plans to remember" maxlength="5000">{{ trip.no'
        "tes }}</textarea></label><button>{{ 'Update plan' if trip.chosen else 'C"
        'onfirm trip\' }}</button></form>{% for a in activities %}<div class="acti'
        'vity"><time>{{ a.day }}</time><span>{{ a.title }}</span><form class="no-'
        'print" method="post" action="{{ url_for(\'delete_activity\',t=trip.id,a=a.'
        'id) }}"><button class="danger" aria-label="Remove {{ a.title }}">Remove<'
        '/button></form></div>{% endfor %}{% if trip.chosen %}<form class="form-r'
        'ow no-print" method="post" action="{{ url_for(\'activity\',t=trip.id) }}">'
        '<label>Date<input type="date" name="day" min="{{ trip.start }}" max="{{ '
        'trip.end }}" required></label><label>Activity<input name="title" placeho'
        'lder="Coffee, a coastal walk, absolutely nothing…" required maxlength="5'
        '00"></label><button>Add activity</button></form>{% endif %}</section>{% '
        'endblock %}\n'
    ),
})
STYLE = (
    ':root{--ink:#183347;--muted:#657886;--blue:#2c83b5;--line:#dce7eb;--paper:#f'
    '7f9f8}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top'
    ':24px}body{margin:0;background:var(--paper);color:var(--ink);font-family:Ari'
    'al,Helvetica,sans-serif;font-size:15px;line-height:1.6}header,main,footer{ma'
    'x-width:1240px;margin:auto}header{height:95px;display:flex;align-items:cente'
    'r;justify-content:space-between;border-bottom:1px solid var(--line);padding:'
    '0 24px}.brand{font-size:29px;font-weight:800;letter-spacing:-1.4px;display:f'
    'lex;gap:10px;align-items:center}.brand> :first-child{color:var(--blue)}.bran'
    'd-dot{color:#e49a69}.header-note{color:var(--muted);font-size:13px}.small-li'
    'nk{font-size:13px}a{color:inherit;text-decoration:none}main{padding:0 24px}h'
    '1,h2,h3,p{margin-top:0}h1{font-size:64px;line-height:1.08;letter-spacing:-3p'
    'x;margin-bottom:24px}h2{font-size:31px;line-height:1.2;letter-spacing:-1px;m'
    'argin-bottom:0}h3{font-size:21px;line-height:1.3;margin-bottom:10px}p{color:'
    'var(--muted)}.eyebrow{font-size:10px;letter-spacing:2px;font-weight:800;colo'
    'r:var(--blue);display:block;margin-bottom:14px}.hero{display:grid;grid-templ'
    'ate-columns:1.05fr 1fr;gap:55px;padding:66px 0 72px;align-items:center}.hero'
    ' p{max-width:420px;font-size:17px;margin-bottom:29px}em{font-style:normal;co'
    'lor:var(--blue)}.button,button{display:inline-block;background:var(--ink);co'
    'lor:white;border:0;border-radius:9px;font:inherit;font-size:13px;font-weight'
    ':700;padding:13px 20px;cursor:pointer;transition:transform .15s,background .'
    '15s}.button:hover,button:hover{background:#29526b;transform:translateY(-1px)'
    '}.hero-caption{margin-top:32px;letter-spacing:1.8px;font-size:9px;color:var('
    '--muted)}.sky-art{height:385px;border-radius:120px 120px 20px 20px;backgroun'
    'd:linear-gradient(155deg,#a9d5e9,#e4f0ef);position:relative;overflow:hidden}'
    '.sun{position:absolute;width:80px;height:80px;top:48px;right:55px;background'
    ':#f5d7a3;border-radius:50%}.orbit{position:absolute;width:370px;height:220px'
    ';border:1px dashed #ffffffbb;border-radius:50%;transform:rotate(-30deg);left'
    ':38px;top:50px}.plane{position:absolute;left:185px;top:58px;font-size:91px;t'
    'ransform:rotate(-22deg);color:white;text-shadow:5px 10px 0 #709cb12b}.cloud{'
    'position:absolute;background:#ffffffaa;border-radius:50px;width:130px;height'
    ":30px}.cloud:before{content:'';position:absolute;background:inherit;border-r"
    'adius:50%;width:60px;height:60px;bottom:0;left:25px}.c1{top:140px;left:-20px'
    '}.c2{top:192px;right:-24px}.ticket{position:absolute;bottom:66px;left:45px;r'
    'ight:45px;padding:25px;background:#fffdf8;border-radius:12px;box-shadow:0 16'
    'px 30px #18334716;transform:rotate(-5deg)}.ticket>span{font-size:8px;letter-'
    'spacing:2px;color:var(--muted)}.ticket strong{display:block;font-size:23px;l'
    'etter-spacing:-.8px;margin:5px 0 13px}.ticket div{border-top:1px dashed #c4d'
    '0d6;padding-top:12px;font-size:9px;letter-spacing:2px}.ticket b{float:right;'
    'font-size:20px}.art-caption{position:absolute;bottom:17px;left:0;right:0;tex'
    't-align:center;font-size:8px;letter-spacing:2px}.section-heading{display:fle'
    'x;justify-content:space-between;align-items:center;gap:20px;margin-bottom:25'
    'px}.section-heading .eyebrow{margin-bottom:9px}.pill{font-size:11px;backgrou'
    'nd:#e8eff1;border-radius:25px;padding:7px 13px;white-space:nowrap;color:#516'
    'b79}.trip-grid,.destination-grid{display:grid;grid-template-columns:repeat(3'
    ',1fr);gap:22px}.trip-card,.destination{border:1px solid var(--line);border-r'
    'adius:14px;overflow:hidden;background:white}.trip-card:hover{box-shadow:0 10'
    'px 25px #18334712}.card-art{height:135px;position:relative;overflow:hidden}.'
    'art-1{background:linear-gradient(140deg,#c7ddd9,#85b5ba)}.art-2{background:l'
    'inear-gradient(140deg,#d7e5ed,#8ca8ba)}.art-0{background:linear-gradient(140'
    'deg,#f2dcbf,#d3b594)}.card-art>span{font-size:105px;color:#ffffffa0;position'
    ':absolute;right:30px;top:-23px;transform:rotate(-15deg)}.card-art small{posi'
    'tion:absolute;left:23px;bottom:18px;font-size:10px;letter-spacing:2px;text-t'
    'ransform:uppercase}.card-body{padding:24px}.card-body p{font-size:13px;min-h'
    'eight:40px}.card-bottom{border-top:1px solid var(--line);padding-top:15px;fo'
    'nt-size:12px;font-weight:bold}.card-bottom span{float:right}.new-trip{displa'
    'y:grid;grid-template-columns:1fr 1.5fr;gap:45px;padding:38px;border:1px soli'
    'd var(--line);background:#edf4f5;border-radius:15px;margin:42px 0 0}label{di'
    'splay:block;font-size:11px;font-weight:bold;margin-bottom:14px;color:#466070'
    '}input,select,textarea{display:block;width:100%;border:1px solid #ccdce3;bac'
    'kground:#fff;border-radius:7px;padding:11px 12px;font:inherit;font-size:14px'
    ';color:var(--ink);margin-top:6px}textarea{resize:vertical}input:focus,select'
    ':focus,textarea:focus{outline:2px solid #81bedb;outline-offset:1px}.form-row'
    '{display:flex;gap:16px;align-items:end;flex-wrap:wrap}.form-row>label{flex:1'
    ';min-width:140px}.form-row>button{margin-bottom:14px}.trip-title{display:fle'
    'x;align-items:center;justify-content:space-between;gap:25px;padding:38px 0 2'
    '5px}.trip-title h1{font-size:45px;margin-bottom:15px;letter-spacing:-2px}.tr'
    'ip-title p{margin-bottom:0}.breadcrumb{display:block;font-size:12px;color:va'
    'r(--muted);margin-bottom:22px}.secondary{color:var(--ink);background:white;b'
    'order:1px solid var(--line)}.secondary:hover{background:#eaf3f6}.tabs{displa'
    'y:flex;border-bottom:1px solid var(--line);gap:32px;padding:18px 0;font-size'
    ':12px;font-weight:bold}.stats{display:grid;grid-template-columns:repeat(4,1f'
    'r);background:#eaf2f4;border-radius:12px;margin:28px 0 48px;padding:24px}.st'
    'ats>div{border-right:1px solid #cfdee4;padding:0 25px}.stats>div:last-child{'
    'border:0}.stats strong{display:block;font-size:29px;letter-spacing:-1px}.sta'
    'ts span{font-size:11px;color:var(--muted)}section[id]{margin-bottom:48px}.mu'
    'ted{font-size:13px}.destination-art{height:170px;position:relative;overflow:'
    "hidden}.destination-art:after{content:'';position:absolute;width:320px;heigh"
    't:180px;background:#ffffff24;border-radius:50%;right:-75px;top:70px}.rank{po'
    'sition:absolute;left:18px;top:14px;font-size:11px;border:1px solid #ffffff77'
    ';border-radius:50%;padding:4px 9px}.landscape{position:absolute;right:25px;t'
    'op:0px;font-size:115px;color:#ffffff8c}.location-label{position:absolute;lef'
    't:24px;bottom:20px;font-size:23px;font-weight:bold;color:var(--ink)}.destina'
    'tion-title{display:flex;justify-content:space-between;gap:12px}.destination-'
    'title>strong{font-size:17px}.metrics{display:flex;justify-content:space-betw'
    'een;gap:8px;font-size:11px}.score{font-size:10px!important;min-height:0!impo'
    'rtant;margin:10px 0 17px}.vote-list{display:flex;flex-wrap:wrap;gap:6px}.vot'
    'e{padding:6px 10px;border:1px solid var(--line);background:white;color:var(-'
    '-muted);font-size:10px}.vote.selected{background:#e5f1f7;color:#247aa5;borde'
    'r-color:#acd1e3}details{background:white;border:1px solid var(--line);border'
    '-radius:9px;padding:16px 20px;margin-top:18px}summary{cursor:pointer;font-si'
    'ze:12px;font-weight:bold}details>form{margin-top:20px}.crew-grid{display:gri'
    'd;grid-template-columns:repeat(2,1fr);gap:18px}.person{padding:22px;backgrou'
    'nd:white;border:1px solid var(--line);border-radius:12px}.person-head{displa'
    'y:flex;gap:13px;align-items:center}.avatar{background:#dceaf1;border-radius:'
    '50%;height:42px;width:42px;text-align:center;line-height:42px;color:var(--bl'
    'ue);font-weight:bold}.person-head h3{font-size:17px;margin:0}.person-head di'
    'v>span{font-size:11px;color:var(--muted)}.date-text{white-space:pre-line;fon'
    't-size:12px;margin:15px 0 0}.person details{padding:10px;border:0;border-top'
    ':1px solid var(--line);border-radius:0}.danger{background:none;color:#b45b49'
    ';padding:7px;font-size:11px}.danger:hover{background:#faeeeb}.windows{border'
    ':1px solid var(--line);border-radius:12px;overflow:hidden;background:white}.'
    'window{display:flex;align-items:center;gap:18px;padding:18px 22px;border-bot'
    'tom:1px solid var(--line)}.window:last-child{border:0}.window>div{flex:1}.wi'
    'ndow strong{font-size:14px}.window p{font-size:11px;margin:3px 0 0}.window-i'
    'con{font-size:22px;color:var(--blue)}.green{background:#e2eee4;color:#477354'
    '}.itinerary{background:#edf4f5;padding:30px;border-radius:14px}.confirmed{bo'
    'rder-bottom:1px dashed #b6cbd5;margin-bottom:25px;padding-bottom:15px}.confi'
    'rmed p{font-size:13px}.preserve{white-space:pre-line}.activity-heading{margi'
    'n-top:30px;font-size:18px}.activity{display:flex;gap:20px;padding:15px 0;bor'
    'der-top:1px solid var(--line);align-items:center}.activity time{font-size:11'
    'px;color:var(--blue)}.activity>span{flex:1;font-size:13px}.empty{padding:25p'
    'x;background:#eef4f6;border-radius:10px;color:var(--muted)}.notice{padding:1'
    '4px 20px;background:#fff3dc;border:1px solid #e9dcbf;border-radius:9px;margi'
    'n:18px 0;font-size:13px}footer{display:flex;justify-content:space-between;pa'
    'dding:30px 24px;border-top:1px solid var(--line);font-size:10px;color:var(--'
    'muted);margin-top:60px}button:focus-visible,a:focus-visible,summary:focus-vi'
    'sible{outline:3px solid #519dc5;outline-offset:3px}@media(max-width:850px){.'
    'hero{gap:25px}h1{font-size:47px}.sky-art{height:340px}.trip-grid,.destinatio'
    'n-grid{grid-template-columns:repeat(2,1fr)}.new-trip{grid-template-columns:1'
    'fr}.header-note{display:none}.stats>div{padding:0 12px}.tabs{gap:20px}.windo'
    'w{flex-wrap:wrap}.window>div{min-width:200px}}@media(max-width:580px){header'
    '{height:74px}.hero{grid-template-columns:1fr;padding:38px 0}.hero h1{font-si'
    'ze:49px}.sky-art{height:300px}.trip-grid,.destination-grid,.crew-grid{grid-t'
    'emplate-columns:1fr}.section-heading{align-items:start;flex-direction:column'
    ';gap:12px}.new-trip{padding:23px;gap:15px}.trip-title{align-items:start;flex'
    '-direction:column}.trip-title h1{font-size:35px}.tabs{overflow:auto;white-sp'
    'ace:nowrap;gap:22px}.stats{grid-template-columns:repeat(2,1fr);gap:20px;padd'
    'ing:20px}.stats>div{border:0}.stats strong{font-size:25px}.window{gap:10px;p'
    'adding:18px}.itinerary{padding:22px}.form-row{display:block}footer{gap:20px}'
    '.ticket{bottom:40px}.hero-caption{margin-top:20px}}@media print{body{backgro'
    'und:white;color:black;font-size:10pt}header,.no-print,footer,details,.tabs{d'
    'isplay:none!important}main{padding:0}.trip-title{padding:0}.trip-title h1{fo'
    'nt-size:28pt}.stats{margin:15px 0;padding:10px}.stats strong{font-size:16pt}'
    'section[id]{margin:20px 0}.section-heading{margin-bottom:10px}h2{font-size:1'
    '8pt}.destination-grid{grid-template-columns:repeat(3,1fr);gap:10px}.destinat'
    'ion-art{height:65px}.landscape,.rank{display:none}.location-label{font-size:'
    '13pt;bottom:10px;left:10px}.card-body{padding:10px}.card-body p{min-height:0'
    '}.crew-grid{gap:10px}.person{padding:10px}.window{padding:8px}.window-icon{d'
    'isplay:none}.itinerary{padding:15px;background:white;border:1px solid #ccc}.'
    'destination,.person,.window,.activity{break-inside:avoid}.notice{background:'
    'white}.pill{white-space:normal}}\n\n.departure-row{display:flex;justify-conten'
    't:center}.departure-row>label{width:calc((100% - 16px)/2)}@media(max-width:5'
    '80px){.departure-row>label{width:100%}}\n\n.departure-row>label{width:100%}.tr'
    'ip-card-link{display:block}.trip-delete{padding:0 24px 18px}.trip-delete .da'
    'nger{border:1px solid #e6c9c2;border-radius:7px;padding:8px 12px}\n\n.destinat'
    'ion-remove{margin-top:16px;border-top:1px solid var(--line);padding-top:10px'
    '}\n'
)

@app.get('/style.css')
def stylesheet():
    return Response(STYLE, mimetype='text/css')

app.secret_key = os.environ.get('CARRYON_SECRET', 'local-carryon-development')
app.config['DATABASE'] = str(ROOT / 'carryon.sqlite3')

@contextmanager
def db():
    con = sqlite3.connect(app.config['DATABASE'])
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        with con:
            yield con
    finally:
        con.close()

def init():
    with db() as c:
        c.executescript("CREATE TABLE IF NOT EXISTS trips(id INTEGER PRIMARY KEY,name TEXT,description TEXT,departure TEXT,chosen INTEGER,start TEXT,end TEXT,accommodation TEXT DEFAULT '',notes TEXT DEFAULT '');\n        CREATE TABLE IF NOT EXISTS people(id INTEGER PRIMARY KEY,trip INTEGER REFERENCES trips(id) ON DELETE CASCADE,name TEXT,budget REAL,length INTEGER,ranges TEXT);\n        CREATE TABLE IF NOT EXISTS destinations(id INTEGER PRIMARY KEY,trip INTEGER REFERENCES trips(id) ON DELETE CASCADE,name TEXT,description TEXT,cost REAL);\n        CREATE TABLE IF NOT EXISTS votes(person INTEGER REFERENCES people(id) ON DELETE CASCADE,destination INTEGER REFERENCES destinations(id) ON DELETE CASCADE,PRIMARY KEY(person,destination));\n        CREATE TABLE IF NOT EXISTS activities(id INTEGER PRIMARY KEY,trip INTEGER REFERENCES trips(id) ON DELETE CASCADE,day TEXT,title TEXT);")
        if 'destination_city' not in {row['name'] for row in c.execute('PRAGMA table_info(trips)')}:
            c.execute("ALTER TABLE trips ADD COLUMN destination_city TEXT DEFAULT ''")

def windows(people):
    """Inclusive travel dates; preferred length is each person's maximum duration."""
    if not people:
        return []
    ranges = {p['id']: [(date.fromisoformat(a), date.fromisoformat(b)) for a,
        b in json.loads(p['ranges'])] for p in people}
    starts = set()
    for rs in ranges.values():
        for a, b in rs:
            starts.update((a + timedelta(days=i) for i in range((b - a).days + 1)))
    results = []
    for start in sorted(starts):
        for length in sorted({p['length'] for p in people}):
            end = start + timedelta(days=length - 1)
            available = [p['name'] for p in people if length <= p['length'] and any((a <= start and end <= b for a,
                b in ranges[p['id']]))]
            if available:
                results.append(dict(start=start.isoformat(), end=end.isoformat(),
                    length=length, names=available, count=len(available)))
    results.sort(key=lambda w: (-w['count'], -w['length'], w['start']))
    return results[:8]

def rank(destinations, people, votes):
    out = []
    for d in destinations:
        item = dict(d)
        item['votes'] = sum((v['destination'] == d['id'] for v in votes))
        item['affordable'] = sum((p['budget'] >= d['cost'] for p in people))
        item['score'] = item['votes'] * 2 + item['affordable']
        out.append(item)
    return sorted(out, key=lambda d: (-d['score'], d['cost'], d['name']))

def redirect_trip(t):
    return redirect(url_for('trip', t=t))

@app.route('/')
def home():
    with db() as c:
        trips = c.execute('SELECT * FROM trips ORDER BY id DESC').fetchall()
    return render_template('home.html', trips=trips)

@app.post('/create')
def create():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Give your trip a name.')
        return redirect(url_for('home'))
    with db() as c:
        t = c.execute('INSERT INTO trips(name,description,departure,destination_city) VALUES(?,?,?,?)',
            (name, '', request.form.get('departure', '').strip(), request.form.get('destination_city',
            '').strip())).lastrowid
    return redirect_trip(t)

@app.get('/trip/<int:t>/remove-confirm/<kind>/<int:item>')
def confirm_remove(t, kind, item):
    routes = {'trip': ('delete_trip', dict(t=t)), 'destination': ('remove_destination',
        dict(t=t, d=item)), 'person': ('remove', dict(t=t, p=item))}
    if kind not in routes:
        return ('Not found', 404)
    endpoint, args = routes[kind]
    return render_template('confirm.html', t=t, kind=kind, action=url_for(endpoint, **args))

@app.post('/trip/<int:t>/delete')
def delete_trip(t):
    with db() as c:
        c.execute('DELETE FROM trips WHERE id=?', (t,))
    flash('Trip deleted.')
    return redirect(url_for('home'))

@app.route('/trip/<int:t>')
def trip(t):
    with db() as c:
        tr = c.execute('SELECT * FROM trips WHERE id=?', (t,)).fetchone()
        if not tr:
            return ('Trip not found', 404)
        people = [dict(p) for p in c.execute('SELECT * FROM people WHERE trip=?', (t,))]
        dests = c.execute('SELECT * FROM destinations WHERE trip=?', (t,)).fetchall()
        votes = c.execute('SELECT v.* FROM votes v JOIN people p ON p.id=v.person WHERE p.trip=?',
            (t,)).fetchall()
        activities = c.execute('SELECT * FROM activities WHERE trip=? ORDER BY day,id',
            (t,)).fetchall()
    for p in people:
        p['ranges_text'] = '\n'.join((a + ' to ' + b for a, b in json.loads(p['ranges'])))
    return render_template('trip.html', trip=tr, people=people, destinations=rank(dests,
        people, votes), windows=windows(people), votes={(v['person'], v['destination']) for v in votes},
        activities=activities, selected_start=request.args.get('start', tr['start'] or ''),
        selected_end=request.args.get('end', tr['end'] or ''))

@app.post('/trip/<int:t>/person')
def person(t):
    try:
        name = request.form['name'].strip()
        budget = float(request.form['budget'])
        length = int(request.form['length'])
        if not name or not 0 <= budget <= 10000000 or (not 1 <= length <= 90):
            raise ValueError()
        ranges = []
        for line in request.form['ranges'].splitlines():
            if not line.strip():
                continue
            a, b = line.strip().split(' to ')
            start = date.fromisoformat(a)
            end = date.fromisoformat(b)
            if end < start or (end - start).days > 366:
                raise ValueError()
            ranges.append([a, b])
        if not ranges:
            raise ValueError()
        with db() as c:
            if request.form.get('id'):
                c.execute('UPDATE people SET name=?,budget=?,length=?,ranges=? WHERE id=? AND trip=?',
                    (name, budget, length, json.dumps(ranges), request.form['id'], t))
            else:
                c.execute('INSERT INTO people(trip,name,budget,length,ranges) VALUES(?,?,?,?,?)',
                    (t, name, budget, length, json.dumps(ranges)))
    except (ValueError, KeyError):
        flash('Check the participant details. Use date ranges like 2027-06-10 to 2027-06-18, one per line; each range can span at most 366 days.')
    return redirect_trip(t)

@app.post('/trip/<int:t>/remove/<int:p>')
def remove(t, p):
    with db() as c:
        c.execute('DELETE FROM people WHERE id=? AND trip=?', (p, t))
    return redirect_trip(t)

@app.post('/trip/<int:t>/destination')
def destination(t):
    try:
        name = request.form['name'].strip()
        cost = float(request.form['cost'])
        if not name or not 0 <= cost <= 10000000:
            raise ValueError()
        with db() as c:
            c.execute('INSERT INTO destinations(trip,name,description,cost) VALUES(?,?,?,?)',
                (t, name, request.form.get('description', ''), cost))
    except (ValueError, KeyError):
        flash('Enter a destination name and a valid nonnegative cost.')
    return redirect_trip(t)

@app.post('/trip/<int:t>/destination/<int:d>/remove')
def remove_destination(t, d):
    with db() as c:
        c.execute('UPDATE trips SET chosen=NULL WHERE id=? AND chosen=?', (t, d))
        c.execute('DELETE FROM destinations WHERE id=? AND trip=?', (d, t))
    return redirect_trip(t)

@app.post('/trip/<int:t>/vote')
def vote(t):
    with db() as c:
        p = c.execute('SELECT id FROM people WHERE id=? AND trip=?',
            (request.form.get('person'), t)).fetchone()
        d = c.execute('SELECT id FROM destinations WHERE id=? AND trip=?',
            (request.form.get('destination'), t)).fetchone()
        if p and d:
            if c.execute('SELECT 1 FROM votes WHERE person=? AND destination=?',
                (p['id'], d['id'])).fetchone():
                c.execute('DELETE FROM votes WHERE person=? AND destination=?', (p['id'], d['id']))
            else:
                c.execute('INSERT INTO votes VALUES(?,?)', (p['id'], d['id']))
    return redirect_trip(t)

@app.post('/trip/<int:t>/confirm')
def confirm(t):
    try:
        start = date.fromisoformat(request.form['start'])
        end = date.fromisoformat(request.form['end'])
        if end < start:
            raise ValueError()
        with db() as c:
            if not c.execute('SELECT id FROM destinations WHERE id=? AND trip=?',
                (request.form['destination'], t)).fetchone():
                raise ValueError()
            c.execute('UPDATE trips SET chosen=?,start=?,end=?,accommodation=?,notes=? WHERE id=?',
                (request.form['destination'], start.isoformat(), end.isoformat(),
                request.form.get('accommodation', ''), request.form.get('notes', ''),
                t))
        flash('Your trip plan is saved. Ready for takeoff!')
    except (ValueError, KeyError):
        flash('Choose a destination and valid travel dates.')
    return redirect_trip(t)

@app.post('/trip/<int:t>/activity')
def activity(t):
    try:
        day = date.fromisoformat(request.form['day'])
        title = request.form['title'].strip()
        if not title:
            raise ValueError()
        with db() as c:
            tr = c.execute('SELECT start,end FROM trips WHERE id=?', (t,)).fetchone()
            if not tr['start'] or not tr['start'] <= day.isoformat() <= tr['end']:
                raise ValueError()
            c.execute('INSERT INTO activities(trip,day,title) VALUES(?,?,?)',
                (t, day.isoformat(), title))
    except (ValueError, KeyError):
        flash('Add an activity with a date inside your confirmed trip.')
    return redirect_trip(t)

@app.post('/trip/<int:t>/activity/<int:a>/delete')
def delete_activity(t, a):
    with db() as c:
        c.execute('DELETE FROM activities WHERE id=? AND trip=?', (a, t))
    return redirect_trip(t)
if __name__ == '__main__':
    init()
    app.run(host='127.0.0.1', port=int(os.environ.get('CARRYON_PORT', '5001')), debug=False)
