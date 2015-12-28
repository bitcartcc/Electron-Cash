from sys import stderr

from electrum_ltc.i18n import _
from electrum_ltc.util import PrintError


class GuiMixin(object):
    # Requires: self.proto, self.device

    messages = {
        3: _("Confirm transaction outputs on %s device to continue"),
        8: _("Confirm transaction fee on %s device to continue"),
        7: _("Confirm message to sign on %s device to continue"),
        10: _("Confirm address on %s device to continue"),
        'change pin': _("Confirm PIN change on %s device to continue"),
        'default': _("Check %s device to continue"),
        'label': _("Confirm label change on %s device to continue"),
        'remove pin': _("Confirm removal of PIN on %s device to continue"),
    }

    def callback_ButtonRequest(self, msg):
        msg_code = self.msg_code_override or msg.code
        message = self.messages.get(msg_code, self.messages['default'])

        if msg.code in [3, 8] and hasattr(self, 'cancel'):
            cancel_callback = self.cancel
        else:
            cancel_callback = None

        self.handler.show_message(message % self.device, cancel_callback)
        return self.proto.ButtonAck()

    def callback_PinMatrixRequest(self, msg):
        if msg.type == 1:
            msg = _("Enter your current %s PIN:")
        elif msg.type == 2:
            msg = _("Enter a new %s PIN:")
        elif msg.type == 3:
            msg = (_("Please re-enter your new %s PIN.\n"
                     "Note the numbers have been shuffled!"))
        else:
            msg = _("Please enter %s PIN")
        pin = self.handler.get_pin(msg % self.device)
        if not pin:
            return self.proto.Cancel()
        return self.proto.PinMatrixAck(pin=pin)

    def callback_PassphraseRequest(self, req):
        msg = _("Please enter your %s passphrase")
        passphrase = self.handler.get_passphrase(msg % self.device)
        if passphrase is None:
            return self.proto.Cancel()
        return self.proto.PassphraseAck(passphrase=passphrase)

    def callback_WordRequest(self, msg):
        # TODO
        stderr.write("Enter one word of mnemonic:\n")
        stderr.flush()
        word = raw_input()
        return self.proto.WordAck(word=word)


def trezor_client_class(protocol_mixin, base_client, proto):
    '''Returns a class dynamically.'''

    class TrezorClient(protocol_mixin, GuiMixin, base_client, PrintError):

        def __init__(self, transport, plugin):
            base_client.__init__(self, transport)
            protocol_mixin.__init__(self, transport)
            self.proto = proto
            self.device = plugin.device
            self.handler = plugin.handler
            self.tx_api = plugin
            self.bad = False
            self.msg_code_override = None

        def change_label(self, label):
            self.msg_code_override = 'label'
            try:
                self.apply_settings(label=label)
            finally:
                self.msg_code_override = None

        def set_pin(self, remove):
            self.msg_code_override = 'remove pin' if remove else 'change pin'
            try:
                self.change_pin(remove)
            finally:
                self.msg_code_override = None

        def firmware_version(self):
            f = self.features
            return (f.major_version, f.minor_version, f.patch_version)

        def atleast_version(self, major, minor=0, patch=0):
            return cmp(self.firmware_version(), (major, minor, patch))

        def call_raw(self, msg):
            try:
                return base_client.call_raw(self, msg)
            except:
                self.print_error("Marking %s client bad" % self.device)
                self.bad = True
                raise

    return TrezorClient
