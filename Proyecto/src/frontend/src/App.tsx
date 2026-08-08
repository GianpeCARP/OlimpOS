import { BrowserRouter, Routes as RouterRoutes, Route } from 'react-router';
import { AppLayout } from './layout/AppLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { RedirectInicial } from './components/RedirectInicial';
import { LoginView } from './views/LoginView';
import { RegistroView } from './views/RegistroView';
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
import { MiProgresoView } from './views/socio/MiProgresoView';
import { MiDietaView } from './views/socio/MiDietaView';
import { MiCuotaView } from './views/socio/MiCuotaView';
import { Snackbar } from './components/ui/Snackbar';
import { ConfirmDialog } from './components/ui/ConfirmDialog';
import { Routes } from './config';

// Routes de config.ts choca de nombre con el componente Routes de
// react-router — se importa aliaseado como RouterRoutes.
// Snackbar/ConfirmDialog van acá (no en AppLayout) para estar disponibles
// también en /login, que no pasa por ese layout.
//
// Cada ruta privada declara su `seccion`: ProtectedRoute la cruza contra la
// matriz de permisos de config.ts, así entrar por URL a algo que el rol no
// puede ver redirige en vez de renderizar.
export default function App() {
  return (
    <BrowserRouter>
      <Snackbar />
      <ConfirmDialog />
      <RouterRoutes>
        <Route path={`/${Routes.LOGIN}`} element={<LoginView />} />
        <Route path={`/${Routes.REGISTRO}`} element={<RegistroView />} />

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
            <Route element={<ProtectedRoute seccion={Routes.MI_PROGRESO} />}>
              <Route path={`/${Routes.MI_PROGRESO}`} element={<MiProgresoView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.MI_DIETA} />}>
              <Route path={`/${Routes.MI_DIETA}`} element={<MiDietaView />} />
            </Route>
            <Route element={<ProtectedRoute seccion={Routes.MI_CUOTA} />}>
              <Route path={`/${Routes.MI_CUOTA}`} element={<MiCuotaView />} />
            </Route>
          </Route>
        </Route>

        <Route path="*" element={<RedirectInicial />} />
      </RouterRoutes>
    </BrowserRouter>
  );
}
