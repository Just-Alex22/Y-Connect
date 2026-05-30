package org.cuerdos.yelena.ui.welcome

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.navigation.fragment.findNavController
import org.cuerdos.yelena.R
import org.cuerdos.yelena.databinding.FragmentWelcomeBinding

class WelcomeFragment : Fragment() {
    private var _b: FragmentWelcomeBinding? = null
    private val b get() = _b!!

    // Permisos necesarios según versión de Android
    private val requiredPermissions = buildList {
        add(Manifest.permission.CAMERA)                    // QR scanner
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            add(Manifest.permission.POST_NOTIFICATIONS)    // Notificaciones (Android 13+)
            add(Manifest.permission.READ_MEDIA_IMAGES)     // Archivos (Android 13+)
            add(Manifest.permission.READ_MEDIA_VIDEO)
            add(Manifest.permission.READ_MEDIA_AUDIO)
        } else {
            add(Manifest.permission.READ_EXTERNAL_STORAGE) // Archivos (< Android 13)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            // Sin WRITE_EXTERNAL_STORAGE en Android 10+ — usa MediaStore
        } else {
            add(Manifest.permission.WRITE_EXTERNAL_STORAGE)
        }
    }

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { _ ->
        // Continuar independientemente — el usuario puede denegar permisos opcionales
        navigateToConnect()
    }

    override fun onCreateView(i: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        _b = FragmentWelcomeBinding.inflate(i, c, false); return b.root
    }

    override fun onViewCreated(v: View, s: Bundle?) {
        super.onViewCreated(v, s)
        b.root.alpha = 0f
        b.root.animate().alpha(1f).setDuration(600).start()

        b.btnComenzar.setOnClickListener {
            requestPermissionsAndContinue()
        }

        b.tvPrivacyPolicy.setOnClickListener {
            startActivity(Intent(Intent.ACTION_VIEW,
                Uri.parse("https://cuerdos.github.io/privacidad")))
        }
    }

    private fun requestPermissionsAndContinue() {
        val missing = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(requireContext(), it) !=
                PackageManager.PERMISSION_GRANTED
        }

        if (missing.isEmpty()) {
            // Todos los permisos ya concedidos
            navigateToConnect()
        } else {
            // Solicitar los que faltan
            permissionLauncher.launch(missing.toTypedArray())
        }
    }

    private fun navigateToConnect() {
        findNavController().navigate(R.id.action_welcome_to_connect)
    }

    override fun onDestroyView() { super.onDestroyView(); _b = null }
}
