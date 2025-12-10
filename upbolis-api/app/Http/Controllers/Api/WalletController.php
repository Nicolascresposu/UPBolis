<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\User;
use App\Models\Wallet;
use App\Models\Transaction;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class WalletController extends Controller
{
    // GET /api/wallet
    public function show(Request $request)
    {
        $user   = $request->user();
        $wallet = $user->wallet()->firstOrCreate(
            [],
            ['balance' => 0]
        );

        return response()->json([
            'wallet' => [
                'id'      => $wallet->id,
                'balance' => (float) $wallet->balance,
            ],
        ]);
    }

    // GET /api/wallet/recipients
    public function recipients(Request $request)
    {
        $user = $request->user();

        $users = User::query()
            ->where('id', '!=', $user->id)
            ->orderBy('name')
            ->get(['id', 'name', 'email']);

        return response()->json([
            'recipients' => $users,
        ]);
    }

    // POST /api/wallet/transfer
    public function transfer(Request $request)
    {
        $user  = $request->user();
        $data  = $request->validate([
            'to_email' => 'required|email',
            'amount'   => 'required|numeric|min:0.01',
            'reason'   => 'nullable|string|max:255',
        ]);

        $reason = $data['reason'] ?? 'Transferencia entre usuarios';

        // Buscar destinatario por email
        $toUser = User::where('email', $data['to_email'])->first();
        if (!$toUser) {
            return response()->json([
                'message' => 'El usuario destino no existe.',
            ], 422);
        }

        if ($toUser->id === $user->id) {
            return response()->json([
                'message' => 'No puedes enviarte UPBolis a ti mismo.',
            ], 422);
        }

        $amount = (float) $data['amount'];

        return DB::transaction(function () use ($user, $toUser, $amount, $reason) {
            $fromWallet = $user->wallet()->lockForUpdate()->firstOrCreate([], ['balance' => 0]);
            $toWallet   = $toUser->wallet()->lockForUpdate()->firstOrCreate([], ['balance' => 0]);

            if ($fromWallet->balance < $amount) {
                return response()->json([
                    'message' => 'Saldo insuficiente para realizar la transferencia.',
                ], 422);
            }

            // Debitar
            $fromWallet->balance -= $amount;
            $fromWallet->save();

            // Acreditar
            $toWallet->balance += $amount;
            $toWallet->save();

            // Registrar transacciones
            Transaction::create([
                'user_id'     => $user->id,
                'type'        => 'transfer_out',
                'amount'      => -$amount,
                'description' => "Enviaste {$amount} UPBolis a {$toUser->email}. {$reason}",
            ]);

            Transaction::create([
                'user_id'     => $toUser->id,
                'type'        => 'transfer_in',
                'amount'      => $amount,
                'description' => "Recibiste {$amount} UPBolis de {$user->email}. {$reason}",
            ]);

            return response()->json([
                'message' => 'Transferencia realizada con éxito.',
            ]);
        });
    }
}
