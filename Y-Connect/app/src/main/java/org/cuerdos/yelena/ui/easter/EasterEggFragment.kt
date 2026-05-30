package org.cuerdos.yelena.ui.easter

import android.os.Bundle
import android.view.*
import androidx.fragment.app.Fragment
import org.cuerdos.yelena.databinding.FragmentEasterBinding

class EasterEggFragment : Fragment() {
    private var _b: FragmentEasterBinding? = null
    private val b get() = _b!!

    override fun onCreateView(i: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        _b = FragmentEasterBinding.inflate(i, c, false); return b.root
    }

    override fun onViewCreated(v: View, s: Bundle?) {
        super.onViewCreated(v, s)
        // Tap para salir
        b.root.setOnClickListener {
            parentFragmentManager.popBackStack()
        }

        // Cargar el GIF con Glide
        try {
            com.bumptech.glide.Glide.with(this)
                .asGif()
                .load(org.cuerdos.yelena.R.raw.easter_gif)
                .into(b.gifView)
        } catch (_: Exception) {}
    }

    override fun onDestroyView() { super.onDestroyView(); _b = null }
}
