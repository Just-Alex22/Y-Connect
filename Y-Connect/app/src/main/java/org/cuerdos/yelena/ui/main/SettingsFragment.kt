package org.cuerdos.yelena.ui.main

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.os.Bundle
import android.view.*
import android.widget.ImageView
import android.widget.LinearLayout
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.os.LocaleListCompat
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import org.cuerdos.yelena.R
import org.cuerdos.yelena.databinding.FragmentSettingsBinding

class SettingsFragment : Fragment() {
    private var _b: FragmentSettingsBinding? = null
    private val b get() = _b!!

    // Temas disponibles: nombre → color hex
    private val themes = listOf(
        "green"  to "#5a7a22",
        "purple" to "#9b59b6",
        "red"    to "#e74c3c",
        "yellow" to "#f39c12",
        "blue"   to "#2980b9",
        "teal"   to "#16a085",
        "pink"   to "#e91e63",
        "orange" to "#e67e22",
    )

    override fun onCreateView(i: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        _b = FragmentSettingsBinding.inflate(i, c, false); return b.root
    }

    override fun onViewCreated(v: View, s: Bundle?) {
        super.onViewCreated(v, s)
        b.root.alpha = 0f; b.root.animate().alpha(1f).setDuration(300).start()
        b.btnBack.setOnClickListener { findNavController().popBackStack() }

        val prefs = requireContext().getSharedPreferences("yelena_prefs", Context.MODE_PRIVATE)

        // ── Tema oscuro/claro ─────────────────────────────────────────────────
        b.switchTheme.isChecked =
            prefs.getInt("theme_mode", AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM) !=
            AppCompatDelegate.MODE_NIGHT_NO
        b.switchTheme.setOnCheckedChangeListener { _, checked ->
            val mode = if (checked) AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM
                       else AppCompatDelegate.MODE_NIGHT_NO
            AppCompatDelegate.setDefaultNightMode(mode)
            prefs.edit().putInt("theme_mode", mode).apply()
        }

        // ── Temas de color ────────────────────────────────────────────────────
        val savedTheme = prefs.getString("accent_theme", "green") ?: "green"
        buildThemePicker(savedTheme, prefs)

        // ── Idioma ────────────────────────────────────────────────────────────
        val activeLang = AppCompatDelegate.getApplicationLocales()
            .toLanguageTags().split(",").firstOrNull()?.take(2)?.ifEmpty { null }
            ?: resources.configuration.locales[0].language

        b.rgLanguage.setOnCheckedChangeListener(null)
        when (activeLang) {
            "es" -> b.rbEs.isChecked = true
            "en" -> b.rbEn.isChecked = true
            "pt" -> b.rbPt.isChecked = true
            "ca" -> b.rbCa.isChecked = true
            "de" -> b.rbDe.isChecked = true
            "fr" -> b.rbFr.isChecked = true
            "ja" -> b.rbJa.isChecked = true
            "ko" -> b.rbKo.isChecked = true
            "it" -> b.rbIt.isChecked = true
            "tr" -> b.rbTr.isChecked = true
            "ru" -> b.rbRu.isChecked = true
            else -> b.rbEs.isChecked = true
        }

        b.rgLanguage.setOnCheckedChangeListener { _, id ->
            val lang = when (id) {
                b.rbEs.id -> "es"; b.rbEn.id -> "en"; b.rbPt.id -> "pt"
                b.rbCa.id -> "ca"; b.rbDe.id -> "de"; b.rbFr.id -> "fr"
                b.rbJa.id -> "ja"; b.rbKo.id -> "ko"; b.rbIt.id -> "it"
                b.rbTr.id -> "tr"; b.rbRu.id -> "ru"
                else -> return@setOnCheckedChangeListener
            }
            if (lang == activeLang) return@setOnCheckedChangeListener
            prefs.edit().putString("language", lang).apply()
            AppCompatDelegate.setApplicationLocales(LocaleListCompat.forLanguageTags(lang))
        }
    }

    private fun buildThemePicker(savedTheme: String, prefs: android.content.SharedPreferences) {
        b.themeColorContainer.removeAllViews()
        val size = (48 * resources.displayMetrics.density).toInt()
        val margin = (8 * resources.displayMetrics.density).toInt()

        themes.forEach { (name, hex) ->
            val dot = ImageView(requireContext()).apply {
                layoutParams = LinearLayout.LayoutParams(size, size).also {
                    it.marginEnd = margin
                }
                setBackgroundResource(R.drawable.shape_dot_theme)
                backgroundTintList = ColorStateList.valueOf(Color.parseColor(hex))
                alpha = if (name == savedTheme) 1f else 0.4f
                setOnClickListener {
                    applyTheme(name, hex, prefs)
                    // Actualizar opacidad de todos los dots
                    (b.themeColorContainer as LinearLayout).let { container ->
                        for (i in 0 until container.childCount) {
                            container.getChildAt(i).alpha = 0.4f
                        }
                    }
                    alpha = 1f
                }
            }
            b.themeColorContainer.addView(dot)
        }
    }

    private fun applyTheme(name: String, hex: String, prefs: android.content.SharedPreferences) {
        prefs.edit().putString("accent_theme", name).putString("accent_color", hex).apply()
        // Notificar al Activity para que actualice el colorPrimary en runtime
        requireActivity().let { act ->
            if (act is org.cuerdos.yelena.ui.MainActivity) {
                act.applyAccentColor(hex)
            }
        }
    }

    override fun onDestroyView() { super.onDestroyView(); _b = null }
}
