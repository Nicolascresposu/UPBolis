<?php

namespace App\Http\Controllers\Api\Admin;

use App\Http\Controllers\Controller;
use App\Models\User;
use App\Models\Wallet;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

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

    // POST /api/admin/users
    // Crear usuario desde el panel admin (via Django)
    public function store(Request $request)
    {
        $validated = $request->validate([
            'name'            => 'required|string|max:255',
            'email'           => 'required|email|unique:users,email',
            'role'            => 'required|in:buyer,seller,admin',
            'password'        => 'nullable|string|min:6',
            'initial_balance' => 'nullable|numeric|min:0',
        ]);

        // Si viene contraseña desde Django, la usamos; si no, generamos una temporal
        $plainPassword = $validated['password'] ?? Str::random(10);

        // Crear usuario
        $user = User::create([
            'name'     => $validated['name'],
            'email'    => $validated['email'],
            'role'     => $validated['role'],
            'password' => Hash::make($plainPassword),
        ]);

        // Crear wallet asociada si no existe
        $wallet = Wallet::firstOrCreate(
            ['user_id' => $user->id],
            ['balance' => 0]
        );

        // Aplicar saldo inicial, si se envió
        if (!empty($validated['initial_balance']) && $validated['initial_balance'] > 0) {
            $wallet->balance += $validated['initial_balance'];
            $wallet->save();
            // Aquí podrías registrar una transacción de tipo "admin_topup" si quieres.
        }

        return response()->json([
            'message' => 'Usuario creado correctamente.',
            'user'    => $user,
            'wallet'  => $wallet,
            // En producción NO conviene devolver la contraseña.
            // 'temp_password' => $plainPassword,
        ], 201);
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

    // PATCH /api/admin/users/{user}/deactivate (stub)
    public function deactivate(User $user)
    {
        return response()->json([
            'message' => 'Funcionalidad de desactivación pendiente de implementación.',
        ]);
    }
}
