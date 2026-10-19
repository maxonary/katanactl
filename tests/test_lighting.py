import unittest
from katanactl.commands import get_lighting_state, set_lighting_color, KatanaError

class HID:
    def __init__(self):
        self.on=True;self.profile=1;self.mode=3;self.color=[77,0,0,255];self.calls=[]
    def send(self,cmd,payload):
        self.calls.append((cmd,payload));sub=payload[0]
        if sub==7:data=bytes([7,int(self.on)])
        elif sub==16:data=bytes([16,self.profile])
        elif sub==9:data=bytes([9,self.profile,self.mode])
        elif sub==11:data=bytes([11,0,3,1,1]+self.color)
        else:
            if sub==8:self.mode=payload[2]
            elif sub==10:self.color=list(payload[5:9])
            elif sub==6:self.on=bool(payload[1])
            return bytes([90,2,10,58,0,sub])+bytes(58)
        return bytes([90,cmd,len(data)])+data+bytes(61-len(data))

class LightingTests(unittest.TestCase):
    def test_read_real_status(self):
        state=get_lighting_state(HID());self.assertTrue(state['enabled']);self.assertEqual(state['rgb'],[255,0,0]);self.assertEqual(state['brightness'],30)
    def test_color_order_and_no_audio_profile_writes(self):
        hid=HID();state=set_lighting_color(hid,240,100,40,True)
        self.assertEqual(state['rgb'],[0,0,255]);self.assertEqual(state['brightness'],40)
        self.assertIn((58,bytes([10,0,3,1,1,102,255,0,0])),hid.calls)
        self.assertTrue(all(cmd==58 for cmd,_ in hid.calls))
    def test_disabled_light_stays_disabled_when_requested(self):
        state=set_lighting_color(HID(),120,100,20,False);self.assertFalse(state['enabled'])
    def test_reject_invalid_color_without_writes(self):
        h=HID()
        with self.assertRaises(ValueError):set_lighting_color(h,361,100,30)
        self.assertEqual(h.calls,[])
    def test_failed_write_cannot_report_success(self):
        class Ignoring(HID):
            def send(self,cmd,payload):
                if payload[0]==10:return bytes([90,2,10,58,0,10])+bytes(58)
                return super().send(cmd,payload)
        with self.assertRaises(KatanaError):set_lighting_color(Ignoring(),240,100,40)

if __name__=='__main__':unittest.main()

class TransportTests(unittest.TestCase):
    def test_ignore_unrelated_lighting_notifications_and_acknowledgements(self):
        from unittest.mock import patch
        from katanactl.transport import KatanaHID
        h=KatanaHID('/dev/test');h._fd=123;h._drain=lambda:None
        frames=iter([bytes([90,58,3,21,1,13]),bytes([90,2,10,58,0,6]),bytes([90,58,9,11,0,3,1,1,77,255,0,0])])
        h._read_with_timeout=lambda:next(frames)
        with patch('katanactl.transport.os.write'):
            response=h.send(58,bytes([11,0,3,1,1,1]))
        self.assertEqual(response[3],11)
