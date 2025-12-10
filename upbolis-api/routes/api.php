<?php

use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\WalletController;
use App\Http\Controllers\Api\ProductController;
use App\Http\Controllers\Api\OrderController;
use App\Http\Controllers\Api\TransactionController;
use App\Http\Controllers\Api\Admin\UserAdminController;
use App\Http\Controllers\Api\Admin\AdminWalletController;
use App\Http\Controllers\Api\Admin\AdminOrderController;
use App\Http\Controllers\Api\Admin\AdminTransactionController;
use App\Http\Controllers\Api\Seller\SellerOrderController;

use Illuminate\Support\Facades\Route;

// ---------- AUTH PÚBLICO (sin login) ----------

Route::prefix('auth')->group(function () {
    Route::post('register', [AuthController::class, 'register']); // crea buyer
    Route::post('login',    [AuthController::class, 'login']);
});

// ---------- TODO LO DEMÁS: LOGIN OBLIGATORIO ----------

Route::middleware('auth:sanctum')->group(function () {

    // --- Perfil básico ---
    Route::get('auth/me',      [AuthController::class, 'me']);
    Route::post('auth/logout', [AuthController::class, 'logout']);

    // ---------- WALLET / UPBolis ----------
    Route::get('wallet',              [WalletController::class, 'show']);       // ver saldo y datos
    Route::get('wallet/recipients',   [WalletController::class, 'recipients']); // LISTA DE DESTINATARIOS
    Route::post('wallet/transfer',    [WalletController::class, 'transfer']);   // transferir UPBolis a otro usuario
    Route::get('transactions',        [TransactionController::class, 'index']); // historial de movimientos de MI wallet

    // ---------- PRODUCTOS (acceso general) ----------
    Route::get('products',           [ProductController::class, 'index']);   // lista de productos activos
    Route::get('products/{product}', [ProductController::class, 'show']);    // ver detalle de un producto

    // ---------- ÓRDENES DEL COMPRADOR (buyer) ----------
    Route::get('orders',          [OrderController::class, 'index']);  // mis órdenes
    Route::get('orders/{order}',  [OrderController::class, 'show']);   // detalle de mi orden
    Route::post('orders',         [OrderController::class, 'store']);  // crear una compra

    // ==================================================
    //                       SELLER
    // ==================================================
    Route::middleware('seller')->prefix('seller')->group(function () {

        // --- Productos del seller ---
        Route::get('products',              [ProductController::class, 'myProducts']);
        Route::post('products',             [ProductController::class, 'store']);
        Route::put('products/{product}',    [ProductController::class, 'update']);
        Route::delete('products/{product}', [ProductController::class, 'destroy']);

        // --- Órdenes relacionadas con mis productos ---
        Route::get('orders',                [SellerOrderController::class, 'index']);
        Route::get('orders/{order}',        [SellerOrderController::class, 'show']);
    });

    // ==================================================
    //                        ADMIN
    // ==================================================
    Route::middleware('admin')->prefix('admin')->group(function () {

        // --- Gestión de usuarios ---
        Route::get('users',                    [UserAdminController::class, 'index']);
        Route::get('users/{user}',             [UserAdminController::class, 'show']);
        Route::post('users',                   [UserAdminController::class, 'store']);  // si luego lo usas
        Route::patch('users/{user}/role',      [UserAdminController::class, 'updateRole']);
        Route::patch('users/{user}/deactivate',[UserAdminController::class, 'deactivate']);

        // --- Gestión de wallets / saldo ---
        Route::get('wallets',                  [AdminWalletController::class, 'index']);
        Route::get('wallets/{user}',           [AdminWalletController::class, 'show']);
        Route::post('wallets/{user}/deposit',  [AdminWalletController::class, 'deposit']);
        Route::post('wallets/{user}/withdraw', [AdminWalletController::class, 'withdraw']);

        // --- Gestión de productos (global) ---
        Route::get('products',                 [ProductController::class, 'index']);
        Route::patch('products/{product}/toggle-active', [ProductController::class, 'toggleActive']);

        // --- Gestión global de órdenes ---
        Route::get('orders',                   [AdminOrderController::class, 'index']);
        Route::get('orders/{order}',           [AdminOrderController::class, 'show']);
        Route::patch('orders/{order}/status',  [AdminOrderController::class, 'updateStatus']);

        // --- Gestión global de transacciones ---
        Route::get('transactions',             [AdminTransactionController::class, 'index']);
        Route::get('users/{user}/transactions',[AdminTransactionController::class, 'byUser']);
    });
});
