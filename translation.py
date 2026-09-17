import os
from config import Config

class Translation(object):
  START_TXT = """<blockquote><b>⚡️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴜʟᴛʀᴀ ғᴏʀᴡᴀʀᴅ ʙᴏᴛ</u></b></blockquote>

👋 <b>Welcome, {}!</b>

An enterprise-grade Telegram channel cloning, media migration, and course distribution engine.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 <b>Engine:</b> <code>🟢 Online & Ready</code>
⚡️ <b>Version:</b> <code>v2.5.0 Ultra Edition</code>
🛡 <b>Anti-Ban Core:</b> <code>Active Jitter & FloodWait Shield</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👇 <i>Choose an action below to get started:</i>"""

  DONATE_TXT = """<blockquote><b>❤️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ sᴜᴘᴘᴏʀᴛ</u></b></blockquote>\n\n<i>Thank you for using Skinet Verse! Your support keeps the servers fast and 100% free.</i>"""

  HELP_TXT = """<blockquote><b>🔆 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴍᴀsᴛᴇʀ ᴄᴏᴍᴍᴀɴᴅ ʜᴜʙ</u></b></blockquote>

<b>📚 Available Commands:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏣ <code>/start</code> — Start bot & view main card
⏣ <code>/forward</code> — Interactive channel forward wizard
⏣ <code>/fwd &lt;link1&gt; &lt;link2&gt;</code> — Instant direct range forward
⏣ <code>/autosave</code> — Real-time 24/7 channel monitoring
⏣ <code>/tutorial</code> — 12-Module Master Knowledge Hub
⏣ <code>/skinet</code> — Skinet Text & Media Modifier Guide
⏣ <code>/referral</code> — Refer & Earn VIP rewards
⏣ <code>/verify</code> — Check verification pass status
⏣ <code>/topref</code> — Top 10 Referral Leaderboard
⏣ <code>/pause</code> / <code>/resume</code> — Pause & resume forward tasks
⏣ <code>/stop</code> — Gracefully cancel ongoing tasks
⏣ <code>/unequify</code> — Channel duplicate message cleaner
⏣ <code>/settings</code> — Complete bot customization menu
⏣ <code>/config</code> — Owner system configuration (Admin)
⏣ <code>/setverify</code> — Token verification config (Admin)
⏣ <code>/userstats</code> — Admin user analytics dashboard
⏣ <code>/reset</code> — Reset configurations to default
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>✨ Key Highlights:</b>
• 🎓 <b>Course Seller Mode:</b> Auto lecture numbering & syllabus TOC
• 🛠 <b>Skinet Modifier:</b> Competitor username & link replacement
• 🚀 <b>Smart AutoSave:</b> Real-time channel listener & auto-post
• ⚡️ <b>Custom Speed:</b> Extreme (0.5s) to Safe (5s) modes"""

  HOW_USE_TXT = """<blockquote><b>📖 <u>ɢᴇᴛᴛɪɴɢ sᴛᴀʀᴛᴇᴅ — ǫᴜɪᴄᴋ sᴇᴛᴜᴘ ɢᴜɪᴅᴇ</u></b></blockquote>

<b>Follow these 3 simple steps to start forwarding:</b>

1️⃣ <b>Add a Bot Token or UserBot:</b>
   • Open <code>/settings</code> ➔ <b>🤖 ʙᴏᴛs</b> ➔ <b>✚ ᴀᴅᴅ ʙᴏᴛ ✚</b>
   • Send your Bot token from @BotFather, or login a UserBot for private channels.

2️⃣ <b>Link Your Target Channel:</b>
   • Open <code>/settings</code> ➔ <b>🏷 ᴄʜᴀɴɴᴇʟs</b> ➔ <b>✚ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ ✚</b>
   • Forward any message from your target channel (ensure bot is Admin!).

3️⃣ <b>Start Forwarding:</b>
   • Send <code>/forward</code> to launch the interactive wizard.
   • Or use <code>/fwd &lt;link1&gt; &lt;link2&gt;</code> for instant batch forwarding!"""

  ABOUT_TXT = """<blockquote><b>ℹ️ <u>ᴀʙᴏᴜᴛ — sᴋɪɴᴇᴛ ᴠᴇʀsᴇ ғᴏʀᴡᴀʀᴅ ʙᴏᴛ</u></b></blockquote>

An enterprise automated media pipeline engineered for high-concurrency channel migration and seamless brand sanitization.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 <b>Bot:</b> <code>Skinet Verse Forward Bot</code>
💎 <b>Edition:</b> <code>Ultra Pro Max v2.5</code>
🗣 <b>Language:</b> <code>Python 3.10+</code>
📚 <b>Framework:</b> <code>Pyrogram / Pyrofork Layer 223+</code>
⚡️ <b>Engine:</b> <code>AsyncIO Multi-Worker</code>
🛡 <b>Security:</b> <code>In-Memory Sessions & FloodWait Defense</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>⚡️ Powered by Skinet Verse Official</i>"""

  STATUS_TXT = """<blockquote><b>📊 <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — sʏsᴛᴇᴍ sᴛᴀᴛᴜs</u></b></blockquote>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 <b>Total Users:</b> <code>{}</code>
🤖 <b>Connected Bots:</b> <code>{}</code>
🔁 <b>Active Forward Tasks:</b> <code>{}</code>
🏷 <b>Connected Channels:</b> <code>{}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━""" 

  SERVER_TXT = """<blockquote><b>⚙️ <u>sᴇʀᴠᴇʀ ʀᴇsᴏᴜʀᴄᴇ sᴛᴀᴛs</u></b></blockquote>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💻 <b>CPU Load:</b> <code>{}%</code>
🧠 <b>RAM Usage:</b> <code>{}%</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
  
  FROM_MSG = "<b>❪ SET SOURCE CHAT ❫\n\nForward the last message or send message link of source chat.\n/cancel - Cancel this process</b>"

  TO_MSG = "<b>❪ CHOOSE TARGET CHAT ❫\n\nChoose your target chat from the buttons below.\n/cancel - Cancel this process</b>"

  SKIP_MSG = "<b><u>sᴇᴛ ɴᴏ. ᴏғ ᴍᴇssᴀɢᴇs ᴛᴏ sᴋɪᴘ 📃</u></b>\n\n<b>You can skip a certain number of messages and forward the rest.\n\nDefault Skip Number = 0</b>\n\n<b><i>Example: If you enter 0, no messages will be skipped.\nIf you enter 5, the first 5 messages will be skipped.</i></b>\n/cancel <b>- Cancel this process</b>"

  CANCEL = "<b>Process Cancelled Successfully!</b>"

  BOT_DETAILS = "<blockquote><b>🤖 <u>ᴄᴏɴɴᴇᴄᴛᴇᴅ ʙᴏᴛ ᴅᴇᴛᴀɪʟs</u></b></blockquote>\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n➣ <b>ɴᴀᴍᴇ:</b> <code>{}</code>\n➣ <b>ʙᴏᴛ ɪᴅ:</b> <code>{}</code>\n➣ <b>ᴜsᴇʀɴᴀᴍᴇ:</b> @{}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  USER_DETAILS = "<blockquote><b>👤 <u>ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴜsᴇʀʙᴏᴛ ᴅᴇᴛᴀɪʟs</u></b></blockquote>\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n➣ <b>ɴᴀᴍᴇ:</b> <code>{}</code>\n➣ <b>ᴜsᴇʀ ɪᴅ:</b> <code>{}</code>\n➣ <b>ᴜsᴇʀɴᴀᴍᴇ:</b> @{}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━"  
         
  TEXT = """<blockquote><b>⚡️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ғᴏʀᴡᴀʀᴅ sᴛᴀᴛᴜs</u></b></blockquote>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 <b>ᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
📥 <b>ғᴇᴛᴄʜᴇᴅ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
📤 <b>ғᴏʀᴡᴀʀᴅᴇᴅ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
♻️ <b>ᴅᴜᴘʟɪᴄᴀᴛᴇ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
🗑 <b>ᴅᴇʟᴇᴛᴇᴅ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
⏩ <b>sᴋɪᴘᴘᴇᴅ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
🚫 <b>ғɪʟᴛᴇʀᴇᴅ ᴍᴇssᴀɢᴇs:</b> <code>{}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡️ <b>sᴛᴀᴛᴜs:</b> <code>{}</code>
📊 <b>ᴘʀᴏɢʀᴇss:</b> <code>{}%</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<blockquote><b>{}</b></blockquote>"""

  DUPLICATE_TEXT = """<blockquote><b>♻️ <u>sᴋɪɴᴇᴛ ᴠᴇʀsᴇ — ᴜɴᴇǫᴜɪғʏ sᴛᴀᴛᴜs</u></b></blockquote>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📥 <b>ғᴇᴛᴄʜᴇᴅ ғɪʟᴇs:</b> <code>{}</code>
🗑 <b>ᴅᴜᴘʟɪᴄᴀᴛᴇ ᴅᴇʟᴇᴛᴇᴅ:</b> <code>{}</code>
⚡️ <b>sᴛᴀᴛᴜs:</b> <code>{}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

  DOUBLE_CHECK = """<blockquote><b>📋 <u>ғᴏʀᴡᴀʀᴅ ᴛᴀsᴋ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ</u></b></blockquote>

<b>Review the task configuration before initiating migration:</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 <b>Active Worker:</b> <code>{botname}</code>
📥 <b>Source Chat:</b> <code>{from_chat}</code>
📤 <b>Target Chat:</b> <code>{to_chat}</code>
⏩ <b>Skip Offset:</b> <code>{skip} msgs</code>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <i><b>Verification Checklist:</b>
• <code>{botname}</code> must be an Admin with post permissions in Target Chat ({to_chat}).
• If Source Chat is private, your UserBot must be a joined member or Admin.</i>

👇 <b>Click "Yes, Proceed" below to start forwarding!</b>""" 

  TERMS_TXT = """<blockquote><b>📜 <u>ᴛᴇʀᴍs ᴏғ sᴇʀᴠɪᴄᴇ — sᴋɪɴᴇᴛ ᴠᴇʀsᴇ</u></b></blockquote>

<b>Last Updated: September 2026</b>

By accessing or using <b>Skinet Verse</b>, you agree to comply with and be bound by the following terms:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>1. Purpose & Permitted Use:</b>
• This bot is provided strictly for educational, personal data migration, and authorized channel backup purposes.
• You must own or have explicit authorization from the channel administrators to migrate, clone, or mirror content.

<b>2. Prohibited Activities:</b>
• Unauthorized distribution of copyrighted media, intellectual property without rights, or proprietary paywalled content.
• Transmission of illicit material, malicious software, spam, mass unauthorized advertising, or content violating Telegram ToS.
• Attempting to reverse engineer, disrupt, or exploit the service infrastructure.

<b>3. Fair Usage & System Stability:</b>
• Strict rate-limiting and anti-flood delay mechanisms are enforced to maintain Telegram MTProto API compliance.
• Abusive automated requests or bypass attempts may result in permanent access revocation.

<b>4. Disclaimer of Warranty:</b>
• The service is provided on an <i>"as is"</i> and <i>"as available"</i> basis without warranties of any kind.
• Operators assume zero legal liability for user-transferred content or channel administrative actions.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>💡 Need help or clarification? Contact support or our administration team.</i>"""

  PRIVACY_TXT = """<blockquote><b>🔒 <u>ᴘʀɪᴠᴀᴄʏ ᴘᴏʟɪᴄʏ — sᴋɪɴᴇᴛ ᴠᴇʀsᴇ</u></b></blockquote>

<b>Last Updated: September 2026</b>

Your privacy, data confidentiality, and account security are our highest architectural priorities.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>1. Zero Content Storage:</b>
• <b>We do not store your forwarded files or media.</b> All media streams transit transiently in-memory directly through official Telegram MTProto endpoints.
• No video, audio, document, or media files ever touch our physical server disks.

<b>2. Session & Credential Security:</b>
• UserBot session strings and Bot tokens are encrypted and isolated within secured MongoDB collections.
• Credentials are used solely to execute forward/autosave tasks initiated by you.
• You can delete your credentials anytime via <code>/settings</code> or <code>/reset</code>.

<b>3. Diagnostics & Telemetry:</b>
• Error diagnostics and task counters (message IDs, success/failure counts) are recorded to facilitate crash recovery and auto-resume.
• System log channels record anonymous event telemetry to troubleshoot Telegram FloodWaits.

<b>4. No Third-Party Sharing:</b>
• We never sell, lease, disclose, or share your Telegram identity, channels, or personal data with any third parties or advertisers.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<i>💡 You retain full sovereignty over your data and can reset your account at any moment.</i>"""