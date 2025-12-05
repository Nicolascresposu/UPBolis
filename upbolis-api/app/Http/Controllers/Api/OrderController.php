<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Order;
use App\Models\OrderItem;
use App\Models\Product;
use App\Models\Transaction;
use App\Models\Wallet;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class OrderController extends Controller
{
    // GET /api/orders → órdenes del usuario logueado (comprador)
    public function index(Request $request)
    {
        $orders = $request->user()
            ->orders()
            ->with('items.product')
            ->latest()
            ->get();

        return response()->json($orders);
    }

    // GET /api/orders/{order} → detalle de una orden del usuario
    public function show(Request $request, Order $order)
    {
        if ($order->user_id !== $request->user()->id) {
            return response()->json(['message' => 'No autorizado'], 403);
        }

        $order->load('items.product');

        return response()->json($order);
    }

    // POST /api/orders → crear una compra que RESTA saldo al buyer y SUMA a los sellers
    public function store(Request $request)
    {
        $data = $request->validate([
            'items'              => 'required|array|min:1',
            'items.*.product_id' => 'required|exists:products,id',
            'items.*.quantity'   => 'required|integer|min:1',
        ]);

        $user = $request->user();

        $order = DB::transaction(function () use ($user, $data) {
            $buyerWallet = $user->wallet;

            if (! $buyerWallet) {
                abort(422, 'El usuario no tiene wallet.');
            }

            $total = 0;

            // Para distribuir el pago entre sellers
            $sellerTotals = []; // [seller_id => monto]
            $itemsData    = [];

            foreach ($data['items'] as $item) {
                $product = Product::findOrFail($item['product_id']);

                if (! $product->is_active) {
                    abort(422, "El producto {$product->name} no está activo.");
                }

                if ($product->stock < $item['quantity']) {
                    abort(422, "Stock insuficiente para {$product->name}.");
                }

                $subtotal = $product->price * $item['quantity'];
                $total   += $subtotal;

                // Acumular para el seller correspondiente
                $sellerId = $product->seller_id;

                if (! $sellerId) {
                    abort(422, "El producto {$product->name} no tiene seller asignado.");
                }

                if (! isset($sellerTotals[$sellerId])) {
                    $sellerTotals[$sellerId] = 0;
                }
                $sellerTotals[$sellerId] += $subtotal;

                $itemsData[] = [
                    'product'    => $product,
                    'quantity'   => $item['quantity'],
                    'unit_price' => $product->price,
                    'subtotal'   => $subtotal,
                    'seller_id'  => $sellerId,
                ];
            }

            if ($buyerWallet->balance < $total) {
                abort(422, 'Saldo insuficiente en la wallet.');
            }

            // 1) Descontar saldo total del comprador
            $buyerWallet->balance -= $total;
            $buyerWallet->save();

            // 2) Pagar a cada seller su parte y crear transacciones
            $transactions = [];

            foreach ($sellerTotals as $sellerId => $amountForSeller) {
                // Asegurarnos de que el seller tiene wallet
                $sellerWallet = Wallet::firstOrCreate(
                    ['user_id' => $sellerId],
                    ['balance' => 0]
                );

                // Acreditar saldo al seller
                $sellerWallet->balance += $amountForSeller;
                $sellerWallet->save();

                // Registrar la transacción buyer -> seller
                $transactions[] = Transaction::create([
                    'from_wallet_id' => $buyerWallet->id,
                    'to_wallet_id'   => $sellerWallet->id,
                    'amount'         => $amountForSeller,
                    'type'           => 'transfer',
                    'description'    => 'Pago por compra de productos',
                ]);
            }

            // Opcional: podrías elegir una transacción principal para enlazar a la orden
            $mainTransactionId = count($transactions) === 1
                ? $transactions[0]->id
                : null;

            // 3) Crear la Order del comprador
            $order = Order::create([
                'user_id'       => $user->id,
                'total_amount'  => $total,
                'status'        => 'paid',
                'transaction_id'=> $mainTransactionId, // puede ser null si hay varios sellers
            ]);

            // 4) Crear OrderItems y disminuir stock de productos
            foreach ($itemsData as $itemData) {
                OrderItem::create([
                    'order_id'   => $order->id,
                    'product_id' => $itemData['product']->id,
                    'quantity'   => $itemData['quantity'],
                    'unit_price' => $itemData['unit_price'],
                    'subtotal'   => $itemData['subtotal'],
                ]);

                $itemData['product']->stock -= $itemData['quantity'];
                $itemData['product']->save();
            }

            return $order->load('items.product');
        });

        return response()->json($order, 201);
    }
}
