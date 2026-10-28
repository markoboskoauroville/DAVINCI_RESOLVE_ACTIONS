#!/usr/bin/env python3
"""fps_presets.py <project> <preset name> — a project's saved settings become a Project Settings preset.

Marko, 26.10.2026: "for davinci, save the preset per frame rate". Resolve's API cannot set the playback frame rate
(read-only) and cannot save a preset; its Project Settings window can, and a preset applied with SetPreset sets the
timeline AND the playback rate (measured: System Config gave 24/24). So a project is set once in that window
(playback field through accessibility), saved, and its SM_Config row — the same blob a preset file holds — is written
into the preset folder as "<preset name>.xml", in the layout of Resolve's own "User Default Config.xml"."""
import os, sqlite3, sys, time, uuid

LIB = os.path.expanduser('~/Library/Application Support/Blackmagic Design/DaVinci Resolve/'
                         'Resolve Project Library/Resolve Projects/Users/guest')
project, name = sys.argv[1], sys.argv[2]
db = os.path.join(LIB, 'Projects', project, 'Project.db')
con = sqlite3.connect('file:%s?mode=ro' % db, uri=True)
blob, = con.execute('select FieldsBlob from SM_Config limit 1').fetchone()
con.close()
default = open(os.path.join(LIB, 'Configs', 'User Default Config.xml')).read()
user = default.split('<User>')[1].split('</User>')[0]
head = default.split('\n')[1]                                   # <!--DbAppVer=... DbPrjVer=...-->
xml = '''<?xml version="1.0" encoding="UTF-8"?>
%s
<SM_Config DbId="%s">
 <FieldsBlob>%s</FieldsBlob>
 <User>%s</User>
 <ConfigId>-1</ConfigId>
 <UserId>0</UserId>
 <ProjId>0</ProjId>
 <SsnId>0</SsnId>
 <Name>%s</Name>
 <LockSysId/>
 <DbSavedTime>%d</DbSavedTime>
 <MultiSysData>
  <Sm2MultiSysData DbId="%s">
   <FieldsBlob/>
   <LockSysId/>
   <DbSavedTime>%d</DbSavedTime>
  </Sm2MultiSysData>
 </MultiSysData>
</SM_Config>
''' % (head, uuid.uuid4(), bytes(blob).hex(), user, name, int(time.time()) % 2**31, uuid.uuid4(), int(time.time()) % 2**31)
out = os.path.join(LIB, 'Configs', name + '.xml')
open(out, 'w').write(xml)
print('preset written:', out)
