<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Transaction;
use App\Models\Wallet;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class WalletController extends Controller
{
    public function show(Request $request)
    {
        $wallet = $request->user()->wallet;

        return response()->json([
            'wallet' => $wallet,
        ]);
    }

    public function transfer(Request $request)
    {
        $data = $request->validate([
            'to_user_id' => 'required|exists:users,id',
            'amount'     => 'required|numeric|min:0.01',
        ]);

        $user = $request->user();

        DB::transaction(function () use ($user, $data) {
            $fromWallet = $user->wallet;
            $toWallet   = Wallet::where('user_id', $data['to_user_id'])->firstOrFail();

            if ($fromWallet->balance < $data['amount']) {
                abort(422, 'Saldo insuficiente');
            }

            $fromWallet->balance -= $data['amount'];
            $fromWallet->save();

            $toWallet->balance += $data['amount'];
            $toWallet->save();

            Transaction::create([
                'from_wallet_id' => $fromWallet->id,
                'to_wallet_id'   => $toWallet->id,
                'amount'         => $data['amount'],
                'type'           => 'transfer',
                'description'    => 'Transferencia UPBolis',
            ]);
        });

        return response()->json(['message' => 'Transferencia realizada']);
    }
}
