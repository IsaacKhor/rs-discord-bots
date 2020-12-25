import telnetlib, threading, socket, sys

class TSErr:
	def __init__(self, eid, msg):
		self.eid = eid
		self.msg = msg

	@staticmethod
	def from_resp_dict(respd):
		try:
			eid = int(respd['id'])
			msg = respd['msg']
			return TSErr(eid, msg)
		except:
			raise ValueError(f'Invalid return code: {str(respd)}')

class TSTextMsg:
	def __init__(self, resp_dict):
		self.msg = resp_dict['msg']
		self.targetmode = int(resp_dict['targetmode'])
		self.invokerid = int(resp_dict['invokerid'])
		self.invokername = resp_dict['invokername']


_ESCAPE_MAP = [
    ("\\", r"\\"),
    ("/", r"\/"),
    (" ", r"\s"),
    ("|", r"\p"),
    ("\a", r"\a"),
    ("\b", r"\b"),
    ("\f", r"\f"),
    ("\n", r"\n"),
    ("\r", r"\r"),
    ("\t", r"\t"),
    ("\v", r"\v")
    ]


def ts_escape(raw):
    for char, replacement in _ESCAPE_MAP:
        raw = raw.replace(char, replacement)
    return raw

def ts_unescape(raw):
    for replacement, char in reversed(_ESCAPE_MAP):
        raw = raw.replace(char, replacement)
    return raw

def format_cmd(cmd, args=dict()):
	fin = cmd
	for k, v in args.items():
		arg = ts_escape(k) + '=' + ts_escape(str(v))
		fin += ' ' + arg
	fin += '\n'
	return fin.encode('UTF-8')

def resp_to_dict(resp):
	toks = resp.decode('UTF-8').strip().split(' ')
	cmd = toks[0]
	toks = toks[1:]
	resp_dict = dict()
	resp_dict['command'] = cmd
	for t in toks:
		if '=' in t:
			k, v = t.split('=', 1)
			resp_dict[k] = ts_unescape(v)
	return resp_dict


class ClientqueryConn:
	def __init__(self, host, port, apikey):
		self._clock = threading.Lock()
		self._conn = telnetlib.Telnet(host, port)

		# 4 welcome lines
		self._readline()
		self._readline()
		self._readline()
		self._readline()

		# Authenticate with clientquery
		self._auth(apikey)

	def _send(self, cmd):
		self._conn.write(cmd)


	def _readline(self):
		recv = self._conn.read_until(b'\n\r')
		return recv


	def _getline_parsed(self):
		return resp_to_dict(self._readline())


	def _ensure_okret(self):
		respd = self._getline_parsed()
		err = TSErr.from_resp_dict(respd)
		if err == None:
			raise ValueError(f'Invalid error: {str(respd)}')
		if err.eid != 0:
			raise ValueError(f'Non-0 return code: {err.id}, message {err.msg}')

		return err


	def _auth(self, apikey):
		cmd = format_cmd('auth', {'apikey': apikey})
		self._send(cmd)
		self._ensure_okret()


	def _whoami(self):
		self._send(format_cmd('whoami'))
		resp = self._getline_parsed()
		self._ensure_okret()
		return int(resp['clid'])


	def _heartbeat(self):
		self._send(format_cmd('whoami'))
		resp = self._getline_parsed()
		self._ensure_okret()


	def set_msg_handler(self, handler):
		self._textmsg_handler = handler


	def start_process_messages(self):
		self._send(format_cmd('clientnotifyregister', {
			'schandlerid': 1,
			'event': 'notifytextmessage'
			}))
		self._ensure_okret()

		while True:
			resp = self._conn.read_until(b'\n\r', timeout=60)
			print(f'Processing: {resp}')
			if len(resp) == 0:
				# Heartbeat
				self._heartbeat()
				continue

			rd = resp_to_dict(resp)
			if rd['command'] != 'notifytextmessage':
				continue

			parsed_msg = TSTextMsg(rd)
			botresp = self._textmsg_handler(parsed_msg)
			print(f'Response: {botresp}')
			if botresp == None:
				continue

			self._send(format_cmd('sendtextmessage', { 
				'targetmode': parsed_msg.targetmode, 
				'target': parsed_msg.invokerid,
				'msg': botresp }))

