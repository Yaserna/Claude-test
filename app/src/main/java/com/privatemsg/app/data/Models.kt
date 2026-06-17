package com.privatemsg.app.data

data class Conversation(
    val threadId: Long,
    val address: String,
    val snippet: String,
    val date: Long,
    val unread: Boolean = false
)

data class Message(
    val id: Long,
    val threadId: Long,
    val address: String,
    val body: String,
    val date: Long,
    val type: Int, // 1 = inbox, 2 = sent
    val subId: Int = -1,
    val status: Int = -1 // Telephony status: 0 = delivered
)
