<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Transaction;
use Illuminate\Http\Request;

class TransactionController extends Controller
{
    // GET /api/transactions → historial de la wallet del usuario
    public function index(Request $request)
    {
        $wallet = $request->user()->wallet;

        $transactions = Transaction::where('from_wallet_id', $wallet->id)
            ->orWhere('to_wallet_id', $wallet->id)
            ->orderByDesc('created_at')
            ->get();

        return response()->json($transactions);
    }
}
