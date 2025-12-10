<?php

namespace Database\Seeders;

use App\Models\Product;
use App\Models\User;
use Illuminate\Database\Seeder;

class ProductSeeder extends Seeder
{
    public function run(): void
    {
        // Obtener el usuario seller creado en SellerUserSeeder
        $seller = User::where('email', 'seller@upbolis.com')->first();

        if (!$seller) {
            $this->command->warn('Seller user not found. Please run SellerUserSeeder first.');
            return;
        }

        // Crear productos de prueba
        $products = [
            [
                'seller_id'   => $seller->id,
                'name'        => 'Laptop Gaming',
                'description' => 'Laptop de alto rendimiento ideal para gaming y desarrollo',
                'price'       => 500,
                'stock'       => 5,
                'is_active'   => true,
            ],
            [
                'seller_id'   => $seller->id,
                'name'        => 'Teclado Mecánico',
                'description' => 'Teclado mecánico RGB con switches Cherry MX',
                'price'       => 80,
                'stock'       => 15,
                'is_active'   => true,
            ],
            [
                'seller_id'   => $seller->id,
                'name'        => 'Mouse Inalámbrico',
                'description' => 'Mouse gamer inalámbrico con batería de larga duración',
                'price'       => 40,
                'stock'       => 20,
                'is_active'   => true,
            ],
            [
                'seller_id'   => $seller->id,
                'name'        => 'Monitor 4K 27"',
                'description' => 'Monitor ultra HD 4K de 27 pulgadas con panel IPS',
                'price'       => 350,
                'stock'       => 3,
                'is_active'   => true,
            ],
            [
                'seller_id'   => $seller->id,
                'name'        => 'Auriculares Premium',
                'description' => 'Auriculares inalámbricos con cancelación de ruido',
                'price'       => 150,
                'stock'       => 10,
                'is_active'   => true,
            ],
            [
                'seller_id'   => $seller->id,
                'name'        => 'SSD 1TB NVMe',
                'description' => 'Unidad de estado sólido NVMe de 1TB para velocidades ultra rápidas',
                'price'       => 100,
                'stock'       => 8,
                'is_active'   => true,
            ],
        ];

        foreach ($products as $product) {
            Product::firstOrCreate(
                [
                    'seller_id' => $product['seller_id'],
                    'name'      => $product['name'],
                ],
                $product
            );
        }

        $this->command->info('Products seeded successfully!');
    }
}
