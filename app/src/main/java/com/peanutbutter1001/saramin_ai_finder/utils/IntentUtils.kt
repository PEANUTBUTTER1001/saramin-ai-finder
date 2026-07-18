package com.peanutbutter1001.saramin_ai_finder.utils

import android.content.Context
import android.content.Intent
import android.net.Uri

object IntentUtils {
    fun openJobUrl(context: Context, url: String) {
        if (!url.startsWith("http")) return

        val recIdx = Uri.parse(url).getQueryParameter("rec_idx")
        
        // Convert to mobile URL if possible. Many apps map their deep links ONLY to the mobile domain (m.saramin.co.kr)
        val targetUrl = if (recIdx != null && url.contains("www.saramin.co.kr")) {
            "https://m.saramin.co.kr/job-search/view?rec_idx=$recIdx"
        } else {
            url
        }

        // 1. Try known custom schemes FIRST. If these work, they are explicit and will definitely route correctly.
        if (recIdx != null) {
            val schemes = listOf(
                "saramin://job-search/view?rec_idx=$recIdx",
                "saraminapp://job-search/view?rec_idx=$recIdx",
                "saramin://jobs/view?rec_idx=$recIdx",
                "saraminapp://jobs/view?rec_idx=$recIdx",
                "saramin://webview?url=${Uri.encode(targetUrl)}",
                "saraminapp://webview?url=${Uri.encode(targetUrl)}"
            )
            for (scheme in schemes) {
                try {
                    val appIntent = Intent(Intent.ACTION_VIEW, Uri.parse(scheme)).apply {
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                    context.startActivity(appIntent)
                    return // Success!
                } catch (e: Exception) {
                    // Ignore and try next scheme
                }
            }
        }

        // 2. Try launching using Intent.URI_INTENT_SCHEME for the mobile URL
        // If the app is installed, this forces it to handle the https targetUrl.
        try {
            val intentUri = targetUrl.replaceFirst("^https?://".toRegex(), "intent://") +
                    "#Intent;scheme=https;package=kr.co.saramin.brandapp;end"
            val intent = Intent.parseUri(intentUri, Intent.URI_INTENT_SCHEME)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            return
        } catch (e: Exception) {
            // Fallback
        }

        // 3. Ultimate Fallback: System web browser
        try {
            val webIntent = Intent(Intent.ACTION_VIEW, Uri.parse(targetUrl)).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(webIntent)
        } catch (webEx: Exception) {
            webEx.printStackTrace()
        }
    }
}
