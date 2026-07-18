package com.peanutbutter1001.saramin_ai_finder

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.ui.Modifier
import com.peanutbutter1001.saramin_ai_finder.navigation.AppNavHost
import com.peanutbutter1001.saramin_ai_finder.ui.theme.SaraminAiFinderTheme
import dagger.hilt.android.AndroidEntryPoint

import androidx.activity.SystemBarStyle
import android.graphics.Color

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(Color.TRANSPARENT)
        )
        setContent {
            SaraminAiFinderTheme {
                AppNavHost(modifier = Modifier.fillMaxSize())
            }
        }
    }
}
