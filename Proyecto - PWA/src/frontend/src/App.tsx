import { useEffect } from 'react';
import { BrowserRouter, Routes as RouterRoutes, Route } from 'react-router';
import { useAuthStore } from './store/authStore';
import { useUiStore } from './store/uiStore';
import { alPerderLaSesion } from './services/api';
import { colors } from './config';
import { AppLayout } from './layout/AppLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { RedirectInicial } from './components/RedirectInicial';
import { LoginView } from './views/LoginView';
import { CambiarPasswordView } from './views/CambiarPasswordView';
import { DashboardView } from './views/dashboard/DashboardView';
import { SociosView } from './views/socios/SociosView';
import { AsistenciaView } from './views/asistencia/AsistenciaView';
import { ActividadesAdminView } from './views/actividades/ActividadesAdminView';
import { CobrosView } from './views/cobros/CobrosView';
import { PersonalView } from './views/personal/PersonalView';
import { RutinasView } from './views/rutinas/RutinasView';
import { NutricionView } from './views/nutricion/NutricionView';
import { UsuariosView } from './views/usuarios/UsuariosView';
import { MiPerfilView } from './views/socio/MiPerfilView';
import { MiRutinaView } from './views/socio/MiRutinaView';
import { MisActividadesView } from './views/socio/MisActividadesView';
import { MisTurnosView } from './views/socio/MisTurnosView';
import { MiProgresoView } from './views/socio/MiProgresoView';
import { MiDietaView } from './views/socio/MiDietaView';
import { MiCuotaView } from './views/socio/MiCuotaView';
import { MisClasesView } from './views/profesor/MisClasesView';
import { Snackbar } from './components/ui/Snackbar';
import { ConfirmDialog } from './components/ui/ConfirmDialog';
import { APP_NAME, Routes } from './config';

// Routes de config.ts choca de nombre con el componente Routes de
// react-router — se importa aliaseado como RouterRoutes.
// Snackbar/ConfirmDialog van acá (no en AppLayout) para estar disponibles
// también en /login, que no pasa por ese layout.
//
// Cada ruta privada declara su `seccion`: ProtectedRoute la cruza contra la
// matriz de permisos de config.ts, así entrar por URL a algo que el rol no
// puede ver redirige en vez de renderizar.
// Pantalla mínima mientras se rehidrata. No es un spinner elaborado a
// propósito: si el backend responde normalmente dura menos de lo que tarda un
// parpadeo, y sólo se ve cuando la API está lenta o dormida (Neon tarda unos
// segundos en despertar tras un rato sin uso).
function Rehidratando() {
  return (
    // min-h-full en vez de min-h-screen, por lo mismo que AppLayout: en iOS
    // `100vh` es mas alto que lo visible y la pantalla de carga quedaba
    // centrada respecto de un alto que no existe.
    <div className="flex min-h-full items-center justify-center bg-surface-base">
      <p className="font-heading text-3xl font-extrabold text-text-main">{APP_NAME}</p>
    </div>
  );
}

export default function App() {
  // Al arrancar —y eso incluye cada F5— se le pregunta al backend por el token
  // que quedó en sessionStorage. Hasta que conteste no se monta el router: si
  // se montara, ProtectedRoute vería isAuthenticated en false y redirigiría al
  // login antes de que llegue la respuesta, con lo cual el F5 seguiría
  // cerrando la sesión.
  const rehidratar = useAuthStore((s) => s.rehidratar);
  const isRehidratando = useAuthStore((s) => s.isRehidratando);

  useEffect(() => {
    void rehidratar();
  }, [rehidratar]);

  // Qué hacer cuando el backend rechaza la sesión en medio del uso (401): se
  // limpia y ProtectedRoute manda al login, con el motivo a la vista. Antes la
  // pantalla se quedaba mostrando errores sin decir que había que volver a
  // entrar — pasa, por ejemplo, al resetearse uno mismo la contraseña.
  useEffect(() => {
    alPerderLaSesion((mensaje) => {
      useAuthStore.getState().sesionPerdida();
      useUiStore.getState().showSnack(mensaje, colors.statusWarn);
    });
  }, []);

  if (isRehidratando) return <Rehidratando />;

  return (
    <BrowserRouter>
      <Snackbar />
      <ConfirmDialog />
      <RouterRoutes>
        {/* Las dos únicas rutas públicas. La de registro se eliminó a
            propósito (consigna: nada de auto-registro). Se sacó la ruta y no
            solo el link del login: dejando la ruta viva, escribir /registro
            en la barra de direcciones seguía abriendo la pantalla — que es
            exactamente el antipatrón de "el front esconde pero no rechaza".

            CAMBIAR_PASSWORD tiene que ser pública porque quien llega ahí no
            tiene sesión: el backend se la negó por tener clave temporal. Se
            protege sola — sin un username pendiente en el store, redirige al
            login. */}
        <Route path={`/${Routes.LOGIN}`} element={<LoginView />} />
        <Route path={`/${Routes.CAMBIAR_PASSWORD}`} element={<CambiarPasswordView />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            {/* La raíz no puede apuntar fijo al dashboard: no todos los
                roles lo ven. RedirectInicial resuelve según el rol. */}
            <Route path="/" element={<RedirectInicial />} />

            <Route element={<ProtectedRoute seccion={Routes.DASHBOARD} />}>
              <Route path={`/${Routes.DASHBOARD}`} element={<DashboardView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.SOCIOS} />}>
              <Route path={`/${Routes.SOCIOS}`} element={<SociosView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.COBROS} />}>
              <Route path={`/${Routes.COBROS}`} element={<CobrosView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.ASISTENCIA} />}>
              <Route path={`/${Routes.ASISTENCIA}`} element={<AsistenciaView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.PERSONAL} />}>
              <Route path={`/${Routes.PERSONAL}`} element={<PersonalView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.RUTINAS} />}>
              <Route path={`/${Routes.RUTINAS}`} element={<RutinasView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.NUTRICION} />}>
              <Route path={`/${Routes.NUTRICION}`} element={<NutricionView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.USUARIOS} />}>
              <Route path={`/${Routes.USUARIOS}`} element={<UsuariosView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.ACTIVIDADES} />}>
              <Route path={`/${Routes.ACTIVIDADES}`} element={<ActividadesAdminView />} />
            </Route>

            {/* Portal del socio. Mismo AppLayout y mismo ProtectedRoute que
                las de gestión —el shell no cambia, sólo el set de nav items
                que el Sidebar decide por rol— pero secciones propias en la
                matriz de permisos: un entrenador que entre por URL a
                /mi-rutina rebota igual que un socio que entre a /socios. */}
            <Route element={<ProtectedRoute seccion={Routes.MI_PERFIL} />}>
              <Route path={`/${Routes.MI_PERFIL}`} element={<MiPerfilView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.MI_RUTINA} />}>
              <Route path={`/${Routes.MI_RUTINA}`} element={<MiRutinaView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.MIS_ACTIVIDADES} />}>
              <Route path={`/${Routes.MIS_ACTIVIDADES}`} element={<MisActividadesView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.MIS_TURNOS} />}>
              <Route path={`/${Routes.MIS_TURNOS}`} element={<MisTurnosView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.MI_PROGRESO} />}>
              <Route path={`/${Routes.MI_PROGRESO}`} element={<MiProgresoView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.MI_DIETA} />}>
              <Route path={`/${Routes.MI_DIETA}`} element={<MiDietaView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.MI_CUOTA} />}>
              <Route path={`/${Routes.MI_CUOTA}`} element={<MiCuotaView />} />
            </Route>

            {/* La pantalla del profesor. Va con las personales y no con las de
                gestión: muestra los turnos de UNA persona, los que dicta ella. */}
            <Route element={<ProtectedRoute seccion={Routes.MIS_CLASES} />}>
              <Route path={`/${Routes.MIS_CLASES}`} element={<MisClasesView />} />
            </Route>
          </Route>
        </Route>

        <Route path="*" element={<RedirectInicial />} />
      </RouterRoutes>
    </BrowserRouter>
  );
}
