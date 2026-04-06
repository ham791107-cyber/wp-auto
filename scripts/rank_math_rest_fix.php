<?php
/**
 * Plugin Name: Rank Math REST API Meta Fix
 * Description: Registers Rank Math SEO meta fields for WordPress REST API write access.
 *              Required for AutoBlog Engine to set focus keywords and SEO meta via API.
 * Version: 1.0
 * Author: PlanX AutoBlog
 */

add_action('init', function () {
    $fields = [
        'rank_math_focus_keyword'  => 'string',
        'rank_math_title'          => 'string',
        'rank_math_description'    => 'string',
        'rank_math_robots'         => 'string',
        'rank_math_canonical_url'  => 'string',
        'rank_math_schema_type'    => 'string',
    ];

    foreach ($fields as $key => $type) {
        register_post_meta('post', $key, [
            'show_in_rest'  => true,
            'single'        => true,
            'type'          => $type,
            'auth_callback' => function () {
                return current_user_can('edit_posts');
            },
        ]);
    }
});
