package com.privatemsg.app.data

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

/**
 * Private local database for hidden messages. These never touch the system
 * SMS store, so they are invisible to everything outside this app.
 */
class HiddenDbHelper(context: Context) :
    SQLiteOpenHelper(context.applicationContext, DB_NAME, null, DB_VERSION) {

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            "CREATE TABLE $TABLE (" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                "address TEXT, " +
                "body TEXT, " +
                "date INTEGER, " +
                "type INTEGER, " +
                "sub_id INTEGER DEFAULT -1, " +
                "status INTEGER DEFAULT -1)"
        )
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        if (oldVersion < 2) {
            db.execSQL("ALTER TABLE $TABLE ADD COLUMN sub_id INTEGER DEFAULT -1")
        }
        if (oldVersion < 3) {
            db.execSQL("ALTER TABLE $TABLE ADD COLUMN status INTEGER DEFAULT -1")
        }
    }

    /** Inserts a message and returns its new row id. */
    fun insert(address: String, body: String, date: Long, type: Int, subId: Int = -1): Long {
        val values = ContentValues().apply {
            put("address", address)
            put("body", body)
            put("date", date)
            put("type", type)
            put("sub_id", subId)
            put("status", -1)
        }
        return writableDatabase.insert(TABLE, null, values)
    }

    /** Updates the delivery status of a hidden message (0 = delivered). */
    fun updateStatus(id: Long, status: Int) {
        val values = ContentValues().apply { put("status", status) }
        writableDatabase.update(TABLE, values, "id = ?", arrayOf(id.toString()))
    }

    /** One entry per distinct hidden address, newest message as snippet. */
    fun getConversations(): List<Conversation> {
        val list = mutableListOf<Conversation>()
        val seen = HashSet<String>()
        readableDatabase.query(
            TABLE, arrayOf("address", "body", "date"),
            null, null, null, null, "date DESC"
        ).use { c ->
            while (c.moveToNext()) {
                val address = c.getString(0) ?: ""
                val key = SecureStore.normalize(address)
                if (!seen.add(key)) continue
                list.add(
                    Conversation(
                        threadId = key.hashCode().toLong(),
                        address = address,
                        snippet = c.getString(1) ?: "",
                        date = c.getLong(2)
                    )
                )
            }
        }
        return list
    }

    fun getMessages(address: String): List<Message> {
        val list = mutableListOf<Message>()
        val target = SecureStore.normalize(address)
        readableDatabase.query(
            TABLE, arrayOf("id", "address", "body", "date", "type", "sub_id", "status"),
            null, null, null, null, "date ASC"
        ).use { c ->
            while (c.moveToNext()) {
                val addr = c.getString(1) ?: ""
                if (SecureStore.normalize(addr) != target) continue
                list.add(
                    Message(
                        id = c.getLong(0),
                        threadId = 0,
                        address = addr,
                        body = c.getString(2) ?: "",
                        date = c.getLong(3),
                        type = c.getInt(4),
                        subId = c.getInt(5),
                        status = c.getInt(6)
                    )
                )
            }
        }
        return list
    }

    fun deleteById(id: Long) {
        writableDatabase.delete(TABLE, "id = ?", arrayOf(id.toString()))
    }

    fun deleteByAddress(address: String) {
        val target = SecureStore.normalize(address)
        val db = writableDatabase
        db.query(TABLE, arrayOf("id", "address"), null, null, null, null, null).use { c ->
            while (c.moveToNext()) {
                val addr = c.getString(1) ?: ""
                if (SecureStore.normalize(addr) == target) {
                    db.delete(TABLE, "id = ?", arrayOf(c.getLong(0).toString()))
                }
            }
        }
    }

    companion object {
        private const val DB_NAME = "hidden.db"
        private const val DB_VERSION = 3
        private const val TABLE = "hidden_sms"
    }
}
