package org.cuerdos.yelena.ui.terminal

import android.os.Bundle
import android.view.*
import android.view.inputmethod.EditorInfo
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import kotlinx.coroutines.launch
import org.cuerdos.yelena.R
import org.cuerdos.yelena.databinding.FragmentTerminalBinding
import org.cuerdos.yelena.model.TerminalOutput
import org.cuerdos.yelena.websocket.YelenaWebSocket

class TerminalFragment : Fragment() {
    private var _b: FragmentTerminalBinding? = null
    private val b get() = _b!!
    private val history = StringBuilder()
    private var waitingForInput = false

    override fun onCreateView(i: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        _b = FragmentTerminalBinding.inflate(i, c, false); return b.root
    }

    override fun onViewCreated(v: View, s: Bundle?) {
        super.onViewCreated(v, s)
        b.root.alpha = 0f; b.root.animate().alpha(1f).setDuration(300).start()
        b.btnBack.setOnClickListener { findNavController().popBackStack() }

        viewLifecycleOwner.lifecycleScope.launch {
            YelenaWebSocket.terminalOutput.collect { output ->
                appendOutput(output)
            }
        }

        b.etCommand.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_SEND) { send(); true } else false
        }
        b.btnSend.setOnClickListener { send() }
    }

    private fun appendOutput(output: TerminalOutput) {
        if (output.output.isNotBlank()) {
            history.append("${output.output}\n")
            b.tvOutput.text = history
            b.scrollOutput.post { b.scrollOutput.fullScroll(View.FOCUS_DOWN) }
        }
        waitingForInput = output.exitCode == null
        updateInputHint()
    }

    private fun updateInputHint() {
        if (waitingForInput) {
            b.etCommand.hint = getString(R.string.terminal_input_hint)
            b.btnSend.setImageResource(R.drawable.ic_send)
        } else {
            b.etCommand.hint = getString(R.string.command_hint)
            b.btnSend.setImageResource(R.drawable.ic_send)
        }
    }

    private fun send() {
        val text = b.etCommand.text.toString()
        if (text.isEmpty()) return
        b.etCommand.text?.clear()
        if (waitingForInput) {
            history.append("${text}\n")
            b.tvOutput.text = history
            b.scrollOutput.post { b.scrollOutput.fullScroll(View.FOCUS_DOWN) }
            YelenaWebSocket.sendTerminalInput(text)
        } else {
            val cmd = text.trim()
            if (cmd.isEmpty()) return
            history.append("$ $cmd\n")
            b.tvOutput.text = history
            b.scrollOutput.post { b.scrollOutput.fullScroll(View.FOCUS_DOWN) }
            YelenaWebSocket.sendTerminalCommand(cmd)
        }
    }

    override fun onDestroyView() { super.onDestroyView(); _b = null }
}