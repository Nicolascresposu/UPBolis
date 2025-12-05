<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Product;
use Illuminate\Http\Request;

class ProductController extends Controller
{
    // GET /api/products  → lista para compradores, sellers, etc.
    public function index()
    {
        $products = Product::where('is_active', true)->get();
        return response()->json($products);
    }

    // GET /api/products/{product}
    public function show(Product $product)
    {
        // podrías ocultar productos inactivos a buyers si quieres:
        if (! $product->is_active) {
            return response()->json(['message' => 'Producto no disponible'], 404);
        }

        return response()->json($product);
    }

    // GET /api/seller/products  → productos del seller logueado
    public function myProducts(Request $request)
    {
        $user = $request->user();

        $products = Product::where('seller_id', $user->id)->get();

        return response()->json($products);
    }

    // POST /api/seller/products  → crear producto (seller o admin)
    public function store(Request $request)
    {
        $user = $request->user(); // seller o admin

        $data = $request->validate([
            'name'        => 'required|string|max:255',
            'description' => 'nullable|string',
            'price'       => 'required|numeric|min:0',
            'stock'       => 'required|integer|min:0',
            'is_active'   => 'boolean',
        ]);

        $data['seller_id'] = $user->id;

        $product = Product::create($data);

        return response()->json($product, 201);
    }

    // PUT /api/seller/products/{product}
    public function update(Request $request, Product $product)
    {
        $user = $request->user();

        // Solo el seller dueño o un admin
        if ($user->role !== 'admin' && $product->seller_id !== $user->id) {
            return response()->json(['message' => 'No autorizado'], 403);
        }

        $data = $request->validate([
            'name'        => 'sometimes|string|max:255',
            'description' => 'sometimes|nullable|string',
            'price'       => 'sometimes|numeric|min:0',
            'stock'       => 'sometimes|integer|min:0',
            'is_active'   => 'sometimes|boolean',
        ]);

        $product->update($data);

        return response()->json($product);
    }

    // DELETE /api/seller/products/{product}
    public function destroy(Request $request, Product $product)
    {
        $user = $request->user();

        if ($user->role !== 'admin' && $product->seller_id !== $user->id) {
            return response()->json(['message' => 'No autorizado'], 403);
        }

        $product->delete();

        return response()->json(['message' => 'Producto eliminado']);
    }
}
