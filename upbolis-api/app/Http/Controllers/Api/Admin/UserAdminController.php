<?php

namespace App\Http\Controllers\Api\Admin;

use App\Http\Controllers\Controller;
use App\Models\User;
use Illuminate\Http\Request;

class UserAdminController extends Controller
{
    // GET /api/admin/users
    public function index()
    {
        $users = User::with('wallet')->orderBy('id', 'asc')->get();

        return response()->json($users);
    }

    // GET /api/admin/users/{user}
    public function show(User $user)
    {
        $user->load('wallet', 'orders');

        return response()->json($user);
    }

    // PATCH /api/admin/users/{user}/role
    public function updateRole(Request $request, User $user)
    {
        $data = $request->validate([
            'role' => 'required|in:admin,seller,buyer',
        ]);

        $user->role = $data['role'];
        $user->save();

        return response()->json([
            'message' => 'Rol actualizado',
            'user'    => $user,
        ]);
    }

    // PATCH /api/admin/users/{user}/deactivate
    // OJO: esto es un stub, para que no rompa.
    // Si quieres desactivar de verdad, agrega un campo is_active en la tabla users.
    public function deactivate(User $user)
    {
        //  agregar campo is_active en users y actualizar
        return response()->json([
            'message' => 'Funcionalidad de desactivación pendiente de implementación.',
        ]);
    }
}
