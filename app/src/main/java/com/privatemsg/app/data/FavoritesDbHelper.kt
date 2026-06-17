package com.privatemsg.app.data

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

data class Favorite(val id: Long, val address: String, val body: String, val date: Long)

/** Stores messages the user marked as favorites. */
class FavoritesDbHelper(context: Context) :
    SQLiteOpenHelper(context.applicationContext, DB_NAME, null, DB_VERSION) {

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            "CREATE TABLE $TABLE (" +
                "id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                "address TEXT, body TEXT, date INTEGER)"
        )
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {}

    fun add(address: String, body: String, date: Long) {
        val values = ContentValues().apply {
            put("address", address)
            put("body", body)
            put("date", date)
        }
        writableDatabase.insert(TABLE, null, values)
    }

    fun getAll(): List<Favorite> {
        val list = mutableListOf<Favorite>()
        readableDatabase.query(
            TABLE, arrayOf("id", "address", "body", "date"),
            null, null, null, null, "date DESC"
        ).use { c ->
            while (c.moveToNext()) {
                list.add(Favorite(c.getLong(0), c.getString(1) ?: "", c.getString(2) ?: "", c.getLong(3)))
            }
        }
        return list
    }

    fun delete(id: Long) {
        writableDatabase.delete(TABLE, "id = ?", arrayOf(id.toString()))
    }

    companion object {
        private const val DB_NAME = "favorites.db"
        private const val DB_VERSION = 1
        private const val TABLE = "favorites"
    }
}
