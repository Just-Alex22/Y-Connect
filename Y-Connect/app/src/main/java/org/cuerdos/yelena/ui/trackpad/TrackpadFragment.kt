package org.cuerdos.yelena.ui.trackpad

import android.content.pm.ActivityInfo
import android.os.Bundle
import android.view.*
import android.widget.LinearLayout
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import com.google.android.material.button.MaterialButton
import org.cuerdos.yelena.R
import org.cuerdos.yelena.databinding.FragmentTrackpadBinding
import org.cuerdos.yelena.websocket.YelenaWebSocket

class TrackpadFragment : Fragment() {

    private var _b: FragmentTrackpadBinding? = null
    private val b get() = _b!!

    private var ctrlActive  = false
    private var shiftActive = false
    private var altActive   = false
    private var superActive = false

    private var currentLayout = Layout.QWERTY

    enum class Layout { QWERTY, SYMBOLS, FN }

    override fun onCreateView(i: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        _b = FragmentTrackpadBinding.inflate(i, c, false)
        return b.root
    }

    override fun onViewCreated(v: View, s: Bundle?) {
        super.onViewCreated(v, s)
        activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE

        b.btnBack.setOnClickListener {
            activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
            findNavController().popBackStack()
        }

        b.btnLayoutQwerty.setOnClickListener  { switchLayout(Layout.QWERTY) }
        b.btnLayoutSymbols.setOnClickListener { switchLayout(Layout.SYMBOLS) }
        b.btnLayoutFn.setOnClickListener      { switchLayout(Layout.FN) }

        b.btnCtrl.setOnClickListener  { toggleMod("ctrl");  refreshMods() }
        b.btnShift.setOnClickListener { toggleMod("shift"); refreshMods() }
        b.btnAlt.setOnClickListener   { toggleMod("alt");   refreshMods() }
        b.btnSuper.setOnClickListener { toggleMod("super"); refreshMods() }

        buildKeyboard()
        refreshMods()
        refreshLayoutTabs()
    }

    private fun toggleMod(mod: String) {
        when (mod) {
            "ctrl"  -> ctrlActive  = !ctrlActive
            "shift" -> shiftActive = !shiftActive
            "alt"   -> altActive   = !altActive
            "super" -> superActive = !superActive
        }
    }

    private fun clearMods() {
        ctrlActive  = false
        shiftActive = false
        altActive   = false
        superActive = false
    }

    private fun sendKey(keyCode: String) {
        val mods = buildList {
            if (ctrlActive)  add("ctrl")
            if (shiftActive) add("shift")
            if (altActive)   add("alt")
            if (superActive) add("super")
        }
        val combo = if (mods.isEmpty()) keyCode else (mods + keyCode).joinToString("+")
        YelenaWebSocket.sendKeyPress(combo)
        clearMods()
        refreshMods()
    }

    private fun buildKeyboard() {
        b.keyboardContainer.removeAllViews()
        when (currentLayout) {
            Layout.QWERTY   -> buildQwerty()
            Layout.SYMBOLS  -> buildSymbols()
            Layout.FN       -> buildFn()
        }
    }

    private fun buildQwerty() {
        addRow(listOf(
            "q" to "Q", "w" to "W", "e" to "E", "r" to "R", "t" to "T",
            "y" to "Y", "u" to "U", "i" to "I", "o" to "O", "p" to "P",
        ))
        addRow(listOf(
            "a" to "A", "s" to "S", "d" to "D", "f" to "F", "g" to "G",
            "h" to "H", "j" to "J", "k" to "K", "l" to "L",
        ))
        addRow(listOf(
            "z" to "Z", "x" to "X", "c" to "C", "v" to "V", "b" to "B",
            "n" to "N", "m" to "M",
        ))
        addRow(listOf(
            "Escape" to "Esc", "Tab" to "Tab", "Return" to "⏎", "BackSpace" to "⌫",
        ))
        addRow(listOf(
            "space" to "Space", "Delete" to "Del",
            "Up" to "▲", "Down" to "▼", "Left" to "◀", "Right" to "▶",
        ))
    }

    private fun buildSymbols() {
        addRow(listOf(
            "1" to "1", "2" to "2", "3" to "3", "4" to "4", "5" to "5",
            "6" to "6", "7" to "7", "8" to "8", "9" to "9", "0" to "0",
        ))
        addRow(listOf(
            "exclam" to "!", "at" to "@", "numbersign" to "#", "dollar" to "$", "percent" to "%",
            "asciicircum" to "^", "ampersand" to "&", "asterisk" to "*",
            "parenleft" to "(", "parenright" to ")",
        ))
        addRow(listOf(
            "minus" to "-", "equal" to "=", "bracketleft" to "[", "bracketright" to "]",
            "semicolon" to ";", "apostrophe" to "'", "comma" to ",", "period" to ".",
            "slash" to "/", "backslash" to "\\",
        ))
        addRow(listOf(
            "grave" to "`", "asciitilde" to "~", "underscore" to "_", "plus" to "+",
            "braceleft" to "{", "braceright" to "}", "colon" to ":", "quotedbl" to "\"",
            "less" to "<", "greater" to ">",
        ))
        addRow(listOf(
            "space" to "Space", "BackSpace" to "⌫", "Return" to "⏎", "Escape" to "Esc",
        ))
    }

    private fun buildFn() {
        addRow(listOf("F1" to "F1", "F2" to "F2", "F3" to "F3", "F4" to "F4", "F5" to "F5", "F6" to "F6"))
        addRow(listOf("F7" to "F7", "F8" to "F8", "F9" to "F9", "F10" to "F10", "F11" to "F11", "F12" to "F12"))
        addRow(listOf(
            "Home" to "Home", "End" to "End",
            "Prior" to "PgUp", "Next" to "PgDn",
            "Up" to "▲", "Down" to "▼", "Left" to "◀", "Right" to "▶",
        ))
        addRow(listOf(
            "Return" to "⏎", "BackSpace" to "⌫", "Delete" to "Del",
            "Tab" to "Tab", "Escape" to "Esc", "space" to "Space",
        ))
        addRow(listOf(
            "Print" to "PrtSc", "Insert" to "Ins", "Pause" to "Pause", "Menu" to "Menu",
        ))
    }

    private fun addRow(keys: List<Pair<String, String>>) {
        val row = LinearLayout(requireContext()).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT,
            ).also { it.bottomMargin = 4.dp }
        }
        keys.forEach { (keyCode, label) ->
            row.addView(makeKey(keyCode, label))
        }
        b.keyboardContainer.addView(row)
    }

    private fun makeKey(keyCode: String, label: String): MaterialButton {
        return MaterialButton(
            requireContext(), null,
            com.google.android.material.R.attr.materialButtonOutlinedStyle,
        ).apply {
            text = label
            textSize = 11f
            setPadding(2.dp, 0, 2.dp, 0)
            insetTop    = 0
            insetBottom = 0
            layoutParams = LinearLayout.LayoutParams(0, 42.dp, 1f).also {
                it.marginEnd = 3.dp
            }
            setOnClickListener { sendKey(keyCode) }
        }
    }

    private fun refreshMods() {
        val accent = ContextCompat.getColor(requireContext(), android.R.color.holo_blue_light)
        val normal = ContextCompat.getColor(requireContext(), R.color.text_primary)
        b.btnCtrl.setTextColor (if (ctrlActive)  accent else normal)
        b.btnShift.setTextColor(if (shiftActive) accent else normal)
        b.btnAlt.setTextColor  (if (altActive)   accent else normal)
        b.btnSuper.setTextColor(if (superActive) accent else normal)
    }

    private fun refreshLayoutTabs() {
        val accent = ContextCompat.getColor(requireContext(), android.R.color.holo_blue_light)
        val normal = ContextCompat.getColor(requireContext(), R.color.text_primary)
        b.btnLayoutQwerty.setTextColor (if (currentLayout == Layout.QWERTY)  accent else normal)
        b.btnLayoutSymbols.setTextColor(if (currentLayout == Layout.SYMBOLS) accent else normal)
        b.btnLayoutFn.setTextColor     (if (currentLayout == Layout.FN)      accent else normal)
    }

    private fun switchLayout(layout: Layout) {
        currentLayout = layout
        buildKeyboard()
        refreshLayoutTabs()
    }

    private val Int.dp get() = (this * resources.displayMetrics.density).toInt()

    override fun onDestroyView() {
        super.onDestroyView()
        activity?.requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
        _b = null
    }
}